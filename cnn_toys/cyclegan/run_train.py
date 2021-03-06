"""Train a CycleGAN model."""

import argparse
import os

import numpy as np
import tensorflow as tf

from cnn_toys.cyclegan.model import CycleGAN
from cnn_toys.data import dir_dataset
from cnn_toys.graphics import save_image_grid
from cnn_toys.saving import save_state, restore_state
from cnn_toys.schedules import half_annealed_lr


def main(args):
    """The main training loop."""
    print('loading datasets...')
    real_x = tf.image.random_flip_left_right(_load_dataset(args.data_dir_1, args.size,
                                                           args.bigger_size))
    real_y = tf.image.random_flip_left_right(_load_dataset(args.data_dir_2, args.size,
                                                           args.bigger_size))
    print('setting up model...')
    model = CycleGAN(real_x, real_y)
    global_step = tf.get_variable('global_step', dtype=tf.int64, shape=(),
                                  initializer=tf.zeros_initializer())
    optimize = model.optimize(
        learning_rate=half_annealed_lr(args.step_size, args.iters, global_step),
        global_step=global_step)
    with tf.Session() as sess:
        print('initializing variables...')
        sess.run(tf.global_variables_initializer())
        print('attempting to restore model...')
        restore_state(sess, args.state_file)
        print('training...')
        while sess.run(global_step) < args.iters:
            terms = sess.run((optimize, model.disc_loss, model.gen_loss, model.cycle_loss))
            step = sess.run(global_step)
            print('step %d: disc=%f gen=%f cycle=%f' % ((step,) + terms[1:]))
            if step % args.sample_interval == 0:
                save_state(sess, args.state_file)
                print('saving samples...')
                _generate_samples(sess, args, model, step)
                _generate_cycle_samples(sess, args, model, step)


def _parse_args():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--data-dir-1', help='first data directory', default='data_1')
    parser.add_argument('--data-dir-2', help='second data directory', default='data_2')
    parser.add_argument('--size', help='image size', type=int, default=256)
    parser.add_argument('--bigger-size', help='size to crop from', type=int, default=286)
    parser.add_argument('--step-size', help='training step size', type=float, default=2e-4)
    parser.add_argument('--state-file', help='state output file', default='state.pkl')
    parser.add_argument('--iters', help='number of training steps', type=int, default=100000)
    parser.add_argument('--sample-interval', help='iters per sample', type=int, default=1000)
    parser.add_argument('--sample-dir', help='directory to dump samples', default='samples')
    parser.add_argument('--sample-count', help='number of samples to draw', type=int, default=16)
    return parser.parse_args()


def _load_dataset(dir_path, size, bigger_size):
    dataset = dir_dataset(dir_path, size, bigger_size=bigger_size)
    return dataset.repeat().make_one_shot_iterator().get_next()


def _generate_samples(sess, args, model, step):
    _generate_grid(sess, args, step, 'samples',
                   (model.real_x, model.gen_y, model.real_y, model.gen_x))


def _generate_cycle_samples(sess, args, model, step):
    _generate_grid(sess, args, step, 'cycles',
                   (model.real_x, model.cycle_x, model.real_y, model.cycle_y))


def _generate_grid(sess, args, step, filename, tensors):
    if not os.path.exists(args.sample_dir):
        os.mkdir(args.sample_dir)
    grid = []
    for _ in range(args.sample_count):
        grid.append(sess.run(tensors))
    save_image_grid(np.array(grid), os.path.join(args.sample_dir, '%s_%d.png' % (filename, step)))


if __name__ == '__main__':
    main(_parse_args())
