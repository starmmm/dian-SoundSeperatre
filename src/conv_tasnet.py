# Created on 2018/12/20
# Author: Kaituo XU

import torch
import torch.nn as nn
import torch.nn.functional as F

EPS = 1e-8


class ConvTasNet(nn.Module):
    def __init__(self, N, L, B, H, P, X, R, C, norm_type="gLN"):
        """
        Args:
            N: Number of filters in autoencoder
            L: Length of the filters (in samples)
            B: Number of channels in bottleneck 1 × 1-conv block
            H: Number of channels in convolutional blocks
            P: Kernel size in convolutional blocks
            X: Number of convolutional blocks in each repeat
            R: Number of repeats
            C: Number of speakers
            norm_type: BN, gLN, cLN
        """
        super(ConvTasNet, self).__init__()
        # Hyper-parameter
        self.N, self.L, self.B, self.H, self.P, self.X, self.R, self.C = N, L, B, H, P, X, R, C
        # Components
        self.encoder = Encoder(L, N)
        self.separator = TemporalConvNet(N, B, H, P, X, R, C, norm_type)
        self.decoder = Decoder(N, L)

    def forward(self, mixture):
        """
        Args:
            mixture: [M, K, L]
        Returns:
            est_source: [M, C, K, L]
        """
        mixture_w = self.encoder(mixture)
        est_mask = self.separator(mixture_w)
        est_source = self.decoder(mixture_w, est_mask)
        return est_source

    @classmethod
    def load_model(cls, path):
        # Load to CPU
        package = torch.load(path, map_location=lambda storage, loc: storage)
        model = cls.load_model_from_package(package)
        return model

    @classmethod
    def load_model_from_package(cls, package):
        model = cls(package['N'], package['L'], package['B'], package['H'],
                    package['P'], package['X'], package['R'], package['C'])
        model.load_state_dict(package['state_dict'])
        return model

    @staticmethod
    def serialize(model, optimizer, epoch, tr_loss=None, cv_loss=None):
        package = {
            # hyper-parameter
            'N': model.N, 'L': model.L, 'B': model.B, 'H': model.H,
            'P': model.P, 'X': model.X, 'R': model.R, 'C': model.C,
            # state
            'state_dict': model.state_dict(),
            'optim_dict': optimizer.state_dict(),
            'epoch': epoch
        }
        if tr_loss is not None:
            package['tr_loss'] = tr_loss
            package['cv_loss'] = cv_loss
        return package


class Encoder(nn.Module):
    """Estimation of the nonnegative mixture weight by a 1-D conv layer.
    """
    def __init__(self, L, N):
        super(Encoder, self).__init__()
        # Hyper-parameter
        self.L, self.N = L, N
        # Components
        # Maybe we can impl 1-D conv by nn.Linear()?
        self.conv1d_U = nn.Conv1d(L, N, kernel_size=1, bias=False)

    def forward(self, mixture):
        """
        Args:
            mixture: [M, K, L], M is batch size
        Returns:
            mixture_w: [M, K, N]
        """
        mixture = mixture.permute((0, 2, 1)).contiguous()  # [M, L, K]
        mixture_w = F.relu(self.conv1d_U(mixture))  # [M, N, K]
        mixture_w = mixture_w.permute((0, 2, 1)).contiguous()
        ### Another implementation
        # M, K, L = mixture.size()
        # mixture = torch.unsqueeze(mixture.view(-1, L), 2)  # [M*K, L, 1]
        # mixture_w = F.relu(self.conv1d_U(mixture))         # [M*K, N, 1]
        # mixture_w = mixture_w.view(B, K, self.N)   # [M, K, N]
        return mixture_w


class Decoder(nn.Module):
    def __init__(self, N, L):
        super(Decoder, self).__init__()
        # Hyper-parameter
        self.N, self.L = N, L
        # Components
        self.basis_signals = nn.Linear(N, L, bias=False)

    def forward(self, mixture_w, est_mask):
        """
        Args:
            mixture_w: [M, K, N]
            est_mask: [M, K, C, N]
        Returns:
            est_source: [M, C, K, L]
        """
        # D = W * M
        source_w = torch.unsqueeze(mixture_w, 2) * est_mask  # M x K x C x N
        # S = DV
        est_source = self.basis_signals(source_w)  # M x K x C x L
        est_source = est_source.permute((0, 2, 1, 3)).contiguous()  # M x C x K x L
        return est_source


class TemporalConvNet(nn.Module):
    def __init__(self, N, B, H, P, X, R, C, norm_type="gLN"):
        """
        Args:
            N: Number of filters in autoencoder
            B: Number of channels in bottleneck 1 × 1-conv block
            H: Number of channels in convolutional blocks
            P: Kernel size in convolutional blocks
            X: Number of convolutional blocks in each repeat
            R: Number of repeats
            C: Number of speakers
            norm_type: BN, gLN, cLN
        """
        super(TemporalConvNet, self).__init__()
        # Hyper-parameter
        self.N, self.B, self.H, self.P, self.X, self.R, self.C = N, B, H, P, X, R, C
        # Components
        # [M, N, K] -> [M, N, K]
        self.layer_norm = ChannelwiseLayerNorm(N)
        # [M, N, K] -> [M, B, K]
        self.bottleneck_conv1x1 = nn.Conv1d(N, B, 1, bias=False)
        # [M, B, K] -> [M, B, K]
        repeats = []
        for r in range(R):
            blocks = []
            for x in range(X):
                dilation = 2**x
                blocks += [TemporalBlock(B, H, P, stride=1,
                                         padding=(P-1)*dilation,
                                         dilation=dilation, norm_type=norm_type)]
            repeats += [nn.Sequential(*blocks)]
        self.temporal_conv_net = nn.Sequential(*repeats)
        # [M, B, K] -> [M, C*N, K]
        self.mask_conv1x1 = nn.Conv1d(B, C*N, 1, bias=False)
        # Put together
        self.network = nn.Sequential(self.layer_norm,
                                     self.bottleneck_conv1x1,
                                     self.temporal_conv_net,
                                     self.mask_conv1x1)

    def forward(self, mixture_w):
        """
        Keep this API same with TasNet
        Args:
            mixture_w: [M, K, N], M is batch size
        returns:
            est_mask: [M, K, C, N]
        """
        M, K, N = mixture_w.size()
        x = mixture_w.permute((0, 2, 1)).contiguous()  # [M, K, N] -> [M, N, K]
        score = self.network(x)  # [M, N, K] -> [M, C*N, K]
        score = score.permute((0, 2, 1)).view(M, K, self.C, N).contiguous() # [M, C*N, K] -> [M, K, C, N]
        est_mask = F.softmax(score, dim=2)
        return est_mask


class TemporalBlock(nn.Module):
    def __init__(self, in_channels, out_channels, kernel_size,
                 stride, padding, dilation, norm_type="gLN"):
        super(TemporalBlock, self).__init__()
        # [M, B, K] -> [M, H, K]
        self.conv1x1 = nn.Conv1d(in_channels, out_channels, 1, bias=False)
        self.prelu = nn.PReLU()
        self.norm = chose_norm(norm_type, out_channels)
        # [M, H, K] -> [M, B, K]
        self.dsconv = DepthwiseSeparableConv(out_channels, in_channels, kernel_size,
                                             stride, padding, dilation, norm_type)
        # Put together
        self.net = nn.Sequential(self.conv1x1, self.prelu, self.norm,
                                 self.dsconv)

    def forward(self, x):
        """
        Args:
            x: [M, B, K]
        Returns:
            [M, B, K]
        """
        residual = x
        out = self.net(x)
        return F.relu(out + residual)


class DepthwiseSeparableConv(nn.Module):
    def __init__(self, in_channels, out_channels, kernel_size,
                 stride, padding, dilation, norm_type="gLN"):
        super(DepthwiseSeparableConv, self).__init__()
        # Use `groups` option to implement depthwise convolution
        # [M, H, K] -> [M, H, K]
        self.depthwise_conv = nn.Conv1d(in_channels, in_channels, kernel_size,
                                        stride=stride, padding=padding,
                                        dilation=dilation, groups=in_channels,
                                        bias=False)
        self.chomp = Chomp1d(padding)
        self.prelu = nn.PReLU()
        self.norm = chose_norm(norm_type, in_channels)
        # [M, H, K] -> [M, B, K]
        self.pointwise_conv = nn.Conv1d(in_channels, out_channels, 1, bias=False)
        # Put together
        self.net = nn.Sequential(self.depthwise_conv, self.chomp, self.prelu, self.norm,
                                 self.pointwise_conv)

    def forward(self, x):
        """
        Args:
            x: [M, H, K]
        Returns:
            result: [M, B, K]
        """
        return self.net(x)


class Chomp1d(nn.Module):
    """To ensure the output length is the same as the input.
    """
    def __init__(self, chomp_size):
        super(Chomp1d, self).__init__()
        self.chomp_size = chomp_size

    def forward(self, x):
        """
        Args:
            x: [M, H, Kpad]
        Returns:
            [M, H, K]
        """
        return x[:, :, :-self.chomp_size].contiguous()


def chose_norm(norm_type, channel_size):
    if norm_type == "gLN":
        return GlobalLayerNorm(channel_size)
    elif norm_type == "cLN":
        return ChannelwiseLayerNorm(channel_size)
    else: # norm_type == "BN":
        return nn.BatchNorm1d(channel_size)


class ChannelwiseLayerNorm(nn.Module):
    """Channel-wise Layer Normalization (cLN)"""
    def __init__(self, channel_size):
        super(ChannelwiseLayerNorm, self).__init__()
        self.gamma = nn.Parameter(torch.Tensor(1, channel_size, 1))  # [1, N, 1]
        self.beta = nn.Parameter(torch.Tensor(1, channel_size,1 ))  # [1, N, 1]
        self.reset_parameters()

    def reset_parameters(self):
        self.gamma.data.fill_(1)
        self.beta.data.zero_()

    def forward(self, y):
        """
        Args:
            y: [M, N, K], M is batch size, N is channel size, K is length
        Returns:
            cLN_y: [M, N, K]
        """
        mean = torch.mean(y, dim=1, keepdim=True)  # [M, 1, K]
        var = torch.var(y, dim=1, keepdim=True, unbiased=False)  # [M, 1, K]
        cLN_y = self.gamma * (y - mean) / torch.pow(var + EPS, 0.5) + self.beta
        return cLN_y


class GlobalLayerNorm(nn.Module):
    """Global Layer Normalization (gLN)"""
    def __init__(self, channel_size):
        super(GlobalLayerNorm, self).__init__()
        self.gamma = nn.Parameter(torch.Tensor(1, channel_size, 1))  # [1, N, 1]
        self.beta = nn.Parameter(torch.Tensor(1, channel_size,1 ))  # [1, N, 1]
        self.reset_parameters()

    def reset_parameters(self):
        self.gamma.data.fill_(1)
        self.beta.data.zero_()

    def forward(self, y):
        """
        Args:
            y: [M, N, K], M is batch size, N is channel size, K is length
        Returns:
            gLN_y: [M, N, K]
        """
        # TODO: in torch 1.0, torch.mean() support dim list
        mean = y.mean(dim=1, keepdim=True).mean(dim=2, keepdim=True) #[M, 1, 1]
        var = torch.pow(y-mean, 2).mean(dim=1, keepdim=True).mean(dim=2, keepdim=True)
        gLN_y = self.gamma * (y - mean) / torch.pow(var + EPS, 0.5) + self.beta
        return gLN_y


if __name__ == "__main__":
    torch.manual_seed(123)
    M, K, N, L = 2, 3, 3, 4
    B, H, P, X, R, C, norm_type = 2, 3, 2, 3, 2, 2, "gLN"
    mixture = torch.randint(3, (M, K, L))
    # test Encoder
    encoder = Encoder(L, N)
    encoder.conv1d_U.weight.data = torch.randint(2, encoder.conv1d_U.weight.size())
    mixture_w = encoder(mixture)
    print('mixture', mixture)
    print('U', encoder.conv1d_U.weight)
    print('mixture_w', mixture_w)

    # test TemporalConvNet
    separator = TemporalConvNet(N, B, H, P, X, R, C, norm_type=norm_type)
    est_mask = separator(mixture_w)
    print('est_mask', est_mask)

    # test Decoder
    decoder = Decoder(N, L)
    est_mask = torch.randint(2, (B, K, C, N))
    est_source = decoder(mixture_w, est_mask)
    print('est_source', est_source)

    # test TasNet
    conv_tasnet = ConvTasNet(N, L, B, H, P, X, R, C, norm_type=norm_type)
    est_source = conv_tasnet(mixture)
    print('est_source', est_source)