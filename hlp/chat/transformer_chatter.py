import os
import sys
import time
import tensorflow as tf
from model.chatter import Chatter
from optparse import OptionParser
import config.get_config as _config
from model.chatter import BeamContainer
from model.transformer.model import model
import model.transformer.model as transformer
from common.pre_treat import preprocess_raw_data


class TransformerChatter(Chatter):
    """
    Transformer模型的聊天类
    """

    def __init__(self, checkpoint_dir, beam_size):
        """
        Transformer聊天器初始化，用于加载模型
        """
        super().__init__(checkpoint_dir)
        self.beam_search_container = BeamContainer(
            beam_size=beam_size,
            max_length=_config.max_length_tar,
            worst_score=1e9,
            length_penalty=6
        )
        self.beam_size = beam_size
        if self.ckpt:
            transformer.checkpoint.restore(tf.train.latest_checkpoint(checkpoint_dir)).expect_partial()

    def init_loss_accuracy(self):
        transformer.train_loss.reset_states()
        transformer.train_accuracy.reset_states()

    def train_step(self, inp, tar, step_loss):
        transformer.train_step(inp, tar)
        step_loss[0] = transformer.train_loss.result()

    def create_predictions(self, inputs, dec_input, t):
        predictions = model(inputs=[inputs, dec_input], training=False)
        predictions = predictions[:, -1:, :]
        # for i in range(self.beam_size):
        #     for k in range(len(predictions[0][0])):
        #         self.beam_search_container.add()
        predicted_id = tf.cast(tf.argmax(predictions, axis=-1), tf.int32)
        dec_input = tf.concat([dec_input, predicted_id], axis=-1)
        predicted_id = tf.squeeze(predicted_id)
        return predicted_id, dec_input


def main():
    parser = OptionParser(version='%transformer chatbot V1.0')
    parser.add_option("-t", "--type", action="store", type="string",
                      dest="type", default="pre_treat",
                      help="execute type, pre_treat/train/chat")
    (options, args) = parser.parse_args()

    # 初始化要使用的聊天器
    chatter = TransformerChatter(checkpoint_dir=_config.transformer_train_data, beam_size=_config.beam_size)

    if options.type == 'train':
        chatter.train(transformer.checkpoint)
    elif options.type == 'chat':
        print("Agent: 你好！结束聊天请输入ESC。")
        while True:
            req = input("User: ")
            if req == "ESC":
                chatter.stop()
                print("Agent: 再见！")
                exit(0)
            response = chatter.respond(req)
            print("Agent: ", response)
    elif options.type == 'pre_treat':
        preprocess_raw_data()
    else:
        print('Error:不存在', sys.argv[2], '模式!')


if __name__ == "__main__":
    """
    Transformer入口：指令需要附带运行参数
    cmd：python transformer_chatter.py -t/--type [执行模式]
    执行类别：pre_treat/train/chat

    chat模式下运行时，输入exit即退出对话
    """
    main()
