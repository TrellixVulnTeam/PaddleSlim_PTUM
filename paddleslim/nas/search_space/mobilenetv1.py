# Copyright (c) 2019  PaddlePaddle Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import numpy as np
import paddle.fluid as fluid
from paddle.fluid.param_attr import ParamAttr
from .search_space_base import SearchSpaceBase
from .base_layer import conv_bn_layer
from .search_space_registry import SEARCHSPACE

__all__ = ["MobileNetV1Space"]


@SEARCHSPACE.register
class MobileNetV1Space(SearchSpaceBase):
    def __init__(self,
                 input_size,
                 output_size,
                 block_num,
                 scale=1.0,
                 class_dim=1000):
        super(MobileNetV1Space, self).__init__(input_size, output_size,
                                               block_num)
        self.scale = scale
        self.class_dim = class_dim
        # self.head_num means the channel of first convolution
        self.head_num = np.array([3, 4, 8, 12, 16, 24, 32])  # 7
        # self.filter_num1 ~ self.filtet_num9 means channel of the following convolution
        self.filter_num1 = np.array([3, 4, 8, 12, 16, 24, 32, 48])  # 8
        self.filter_num2 = np.array([8, 12, 16, 24, 32, 48, 64, 80])  # 8
        self.filter_num3 = np.array(
            [16, 24, 32, 48, 64, 80, 96, 128, 144, 160])  #10
        self.filter_num4 = np.array(
            [24, 32, 48, 64, 80, 96, 128, 144, 160, 192])  #10
        self.filter_num5 = np.array(
            [32, 48, 64, 80, 96, 128, 144, 160, 192, 224, 256, 320])  #12
        self.filter_num6 = np.array(
            [64, 80, 96, 128, 144, 160, 192, 224, 256, 320, 384])  #11
        self.filter_num7 = np.array([
            64, 80, 96, 128, 144, 160, 192, 224, 256, 320, 384, 512, 1024, 1048
        ])  #14
        self.filter_num8 = np.array(
            [128, 144, 160, 192, 224, 256, 320, 384, 512, 576, 640, 704,
             768])  #13
        self.filter_num9 = np.array(
            [160, 192, 224, 256, 320, 384, 512, 640, 768, 832, 1024,
             1048])  #12
        # self.k_size means kernel size
        self.k_size = np.array([3, 5])  #2
        # self.repeat means repeat_num in forth downsample 
        self.repeat = np.array([1, 2, 3, 4, 5, 6])  #6

        assert self.block_num < 6, 'MobileNetV1: block number must less than 6, but receive block number is {}'.format(
            self.block_num)

    def init_tokens(self):
        """
        The initial token.
        The first one is the index of the first layers' channel in self.head_num,
        each line in the following represent the index of the [filter_num1, filter_num2, kernel_size]
        and depth means repeat times for forth downsample
        """
        # yapf: disable
        base_init_tokens = [6,  # 32
            6, 6, 0,  # 32, 64, 3
            6, 7, 0,  # 64, 128, 3
            7, 6, 0,  # 128, 128, 3
            6, 10, 0,  # 128, 256, 3
            10, 8, 0,  # 256, 256, 3
            8, 11, 0,  # 256, 512, 3
            4,  # depth 5
            11, 8, 0,  # 512, 512, 3
            8, 10, 0,  # 512, 1024, 3
            10, 10, 0]  # 1024, 1024, 3
        # yapf: enable
        if self.block_num < 5:
            self.token_len = 1 + (self.block_num * 2 - 1) * 3
        else:
            self.token_len = 2 + (self.block_num * 2 - 1) * 3
        return base_init_tokens[:self.token_len]

    def range_table(self):
        """
        Get range table of current search space, constrains the range of tokens.
        """
        base_range_table = [
            len(self.head_num), len(self.filter_num1), len(self.filter_num2),
            len(self.k_size), len(self.filter_num2), len(self.filter_num3),
            len(self.k_size), len(self.filter_num3), len(self.filter_num4),
            len(self.k_size), len(self.filter_num4), len(self.filter_num5),
            len(self.k_size), len(self.filter_num5), len(self.filter_num6),
            len(self.k_size), len(self.filter_num6), len(self.filter_num7),
            len(self.k_size), len(self.repeat), len(self.filter_num7),
            len(self.filter_num8), len(self.k_size), len(self.filter_num8),
            len(self.filter_num9), len(self.k_size), len(self.filter_num9),
            len(self.filter_num9), len(self.k_size)
        ]
        return base_range_table[:self.token_len]

    def token2arch(self, tokens=None):

        if tokens is None:
            tokens = self.tokens()

        bottleneck_param_list = []

        if self.block_num >= 1:
            # tokens[0] = 32
            # 32, 64
            bottleneck_param_list.append(
                (self.filter_num1[tokens[1]], self.filter_num2[tokens[2]], 1,
                 self.k_size[tokens[3]]))
        if self.block_num >= 2:
            # 64 128 128 128
            bottleneck_param_list.append(
                (self.filter_num2[tokens[4]], self.filter_num3[tokens[5]], 2,
                 self.k_size[tokens[6]]))
            bottleneck_param_list.append(
                (self.filter_num3[tokens[7]], self.filter_num4[tokens[8]], 1,
                 self.k_size[tokens[9]]))
        if self.block_num >= 3:
            # 128 256 256 256
            bottleneck_param_list.append(
                (self.filter_num4[tokens[10]], self.filter_num5[tokens[11]], 2,
                 self.k_size[tokens[12]]))
            bottleneck_param_list.append(
                (self.filter_num5[tokens[13]], self.filter_num6[tokens[14]], 1,
                 self.k_size[tokens[15]]))
        if self.block_num >= 4:
            # 256 512 (512 512) *  5
            bottleneck_param_list.append(
                (self.filter_num6[tokens[16]], self.filter_num7[tokens[17]], 2,
                 self.k_size[tokens[18]]))
            for i in range(self.repeat[tokens[19]]):
                bottleneck_param_list.append(
                    (self.filter_num7[tokens[20]],
                     self.filter_num8[tokens[21]], 1, self.k_size[tokens[22]]))
        if self.block_num >= 5:
            # 512 1024 1024 1024
            bottleneck_param_list.append(
                (self.filter_num8[tokens[23]], self.filter_num9[tokens[24]], 2,
                 self.k_size[tokens[25]]))
            bottleneck_param_list.append(
                (self.filter_num9[tokens[26]], self.filter_num9[tokens[27]], 1,
                 self.k_size[tokens[28]]))

        def net_arch(input):
            input = conv_bn_layer(
                input=input,
                filter_size=3,
                num_filters=self.head_num[tokens[0]],
                stride=2,
                name='mobilenetv1')

            for i, layer_setting in enumerate(bottleneck_param_list):
                filter_num1, filter_num2, stride, kernel_size = layer_setting
                input = self._depthwise_separable(
                    input=input,
                    num_filters1=filter_num1,
                    num_filters2=filter_num2,
                    num_groups=filter_num1,
                    stride=stride,
                    scale=self.scale,
                    kernel_size=kernel_size,
                    name='mobilenetv1_{}'.format(str(i + 1)))

            if self.output_size == 1:
                print('NOTE: if output_size is 1, add fc layer in the end!!!')
                input = fluid.layers.fc(
                    input=input,
                    size=self.class_dim,
                    param_attr=ParamAttr(name='mobilenetv2_fc_weights'),
                    bias_attr=ParamAttr(name='mobilenetv2_fc_offset'))
            else:
                assert self.output_size == input.shape[2], \
                          ("output_size must EQUAL to input_size / (2^block_num)."
                          "But receive input_size={}, output_size={}, block_num={}".format(
                          self.input_size, self.output_size, self.block_num))

            return input

        return net_arch

    def _depthwise_separable(self,
                             input,
                             num_filters1,
                             num_filters2,
                             num_groups,
                             stride,
                             scale,
                             kernel_size,
                             name=None):
        depthwise_conv = conv_bn_layer(
            input=input,
            filter_size=kernel_size,
            num_filters=int(num_filters1 * scale),
            stride=stride,
            num_groups=int(num_groups * scale),
            use_cudnn=False,
            name=name + '_dw')
        pointwise_conv = conv_bn_layer(
            input=depthwise_conv,
            filter_size=1,
            num_filters=int(num_filters2 * scale),
            stride=1,
            name=name + '_sep')

        return pointwise_conv
