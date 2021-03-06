import tensorflow as tf
import copy


# Beam search类
class BeamSearch(object):
    """
    BeamSearch使用说明：
    1.首先需要将问句编码成token向量并对齐，然后调用init_input方法进行初始化
    2.对模型要求能够进行批量输入
    3.BeamSearch使用实例已经集成到Chatter中，如果不进行自定义调用，
    可以将聊天器继承Chatter，在满足上述两点的基础之上设计_create_predictions方法，并调用BeamSearch
    """

    def __init__(self, beam_size, max_length, worst_score):
        """
        初始化BeamSearch的序列容器
        """
        self.remain_beam_size = beam_size
        self.max_length = max_length - 1
        self.remain_worst_score = worst_score
        self._reset_variables()

    def __len__(self):
        """
        已存在BeamSearch的序列容器的大小
        """
        return len(self.container)

    def init_variables(self, inputs, dec_input):
        """
        用来初始化输入
        :param inputs: 已经序列化的输入句子
        :param dec_input: 编码器输入序列
        :return: 无返回值
        """
        self.container.append((1, dec_input))
        self.inputs = inputs
        self.dec_inputs = dec_input

    def get_variables(self):
        """
        用来动态的更新模型的inputs和dec_inputs，以适配随着Beam Search
        结果的得出而变化的beam_size
        :return: requests, dec_inputs
        """
        # 生成多beam输入
        inputs = self.inputs
        for i in range(len(self) - 1):
            inputs = tf.concat([inputs, self.inputs], 0)
        requests = inputs
        # 生成多beam的decoder的输入
        temp = self.container[0][1]
        for i in range(1, len(self)):
            temp = tf.concat([temp, self.container[i][1]], axis=0)
        self.dec_inputs = copy.deepcopy(temp)
        return requests, self.dec_inputs

    def _reduce_end(self, end_sign):
        """
        当序列遇到了结束token，需要将该序列从容器中移除
        :return: 无返回值
        """
        for idx, (s, dec) in enumerate(self.container):
            temp = dec.numpy()
            if temp[0][-1] == end_sign:
                self.result.append(self.container[idx][1])
                del self.container[idx]
                self.beam_size -= 1

    def _reset_variables(self):
        """
        重置相关变量
        :return: 无返回值
        """
        self.beam_size = self.remain_beam_size
        self.worst_score = self.remain_worst_score
        self.container = []  # 保存中间状态序列的容器，元素格式为(score, sequence)类型为(float, [])
        self.result = []  # 用来保存已经遇到结束符的序列
        self.inputs = tf.constant(0, shape=(1, 1))
        self.dec_inputs = tf.constant(0, shape=(1, 1))  # 处理后的的编码器输入

    def add(self, predictions, end_sign):
        """
        往容器中添加预测结果，在本方法中对预测结果进行整理、排序的操作
        :param predictions: 传入每个时间步的模型预测值
        :return: 无返回值
        """
        remain = copy.deepcopy(self.container)
        for i in range(self.dec_inputs.shape[0]):
            for k in range(predictions.shape[-1]):
                if predictions[i][k] <= 0:
                    continue
                # 计算分数
                score = remain[i][0] * predictions[i][k]
                # 判断容器容量以及分数比较

                if len(self) < self.beam_size or score > self.worst_score:
                    self.container.append((score, tf.concat([remain[i][1], tf.constant([[k]], shape=(1, 1))], axis=-1)))
                    if len(self) > self.beam_size:
                        sorted_scores = sorted([(s, idx) for idx, (s, _) in enumerate(self.container)])
                        del self.container[sorted_scores[0][1]]
                        self.worst_score = sorted_scores[1][0]
                    else:
                        self.worst_score = min(score, self.worst_score)
        self._reduce_end(end_sign=end_sign)

    def get_result(self):
        """
        获取最终beam个序列
        :return: beam个序列
        """
        result = self.result

        # 每轮回答之后，需要重置容器内部的相关变量值
        self._reset_variables()
        return result
