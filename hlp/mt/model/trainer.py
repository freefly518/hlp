import tensorflow as tf
from model import network
from common import self_attention
from config import get_config as _config
import time
from common import preprocess


def train_step(inp, tar, transformer, optimizer, train_loss, train_accuracy):
    tar_inp = tar[:, :-1]
    tar_real = tar[:, 1:]

    enc_padding_mask, combined_mask, dec_padding_mask = self_attention.create_masks(inp, tar_inp)

    with tf.GradientTape() as tape:
        predictions, _ = transformer(inp, tar_inp,
                                     True,
                                     enc_padding_mask,
                                     combined_mask,
                                     dec_padding_mask)
        loss = network.loss_function(tar_real, predictions)

    gradients = tape.gradient(loss, transformer.trainable_variables)
    optimizer.apply_gradients(zip(gradients, transformer.trainable_variables))

    train_loss(loss)
    train_accuracy(tar_real, predictions)
    return transformer, optimizer, train_loss, train_accuracy


def train(input_tensor, target_tensor, transformer, optimizer, train_loss, train_accuracy):

    train_dataset, val_dataset = preprocess.split_batch(input_tensor, target_tensor)
    checkpoint_path = _config.checkpoint_path

    ckpt = tf.train.Checkpoint(transformer=transformer,
                               optimizer=optimizer)

    ckpt_manager = tf.train.CheckpointManager(ckpt, checkpoint_path, max_to_keep=5)

    # 如果检查点存在，则恢复最新的检查点。
    if ckpt_manager.latest_checkpoint:
        ckpt.restore(ckpt_manager.latest_checkpoint)
        print('已恢复至最新检查点！')

    print("开始训练...")
    for epoch in range(_config.EPOCHS):
        print('Epoch {}/{}'.format(epoch + 1, _config.EPOCHS))
        start = time.time()

        train_loss.reset_states()
        train_accuracy.reset_states()

        batch_sum = 0
        sample_sum = int(len(input_tensor) * (1 - _config.test_size))

        # inp -> english, tar -> chinese
        for (batch, (inp, tar)) in enumerate(train_dataset):
            transformer, optimizer, train_loss, train_accuracy = \
                train_step(inp, tar, transformer, optimizer, train_loss, train_accuracy)
            batch_sum = batch_sum + len(inp)
            print('\r{}/{} [==================================]'.format(batch_sum, sample_sum), end='')

        step_time = (time.time() - start)
        print(' - {:.4f}s/step - loss: {:.4f} - Accuracy {:.4f}\n'
                         .format(step_time, train_loss.result(), train_accuracy.result()), end='\n')

        if (epoch + 1) % 5 == 0:
            ckpt_save_path = ckpt_manager.save()
            print('Saving checkpoint for epoch {} at {}'.format(epoch + 1,
                                                                ckpt_save_path))
    print('训练完毕！')


