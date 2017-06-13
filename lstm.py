from __future__ import print_function

import json
import numpy as np
import sys
import os
import cPickle
import random
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import time

from keras.models import Sequential, load_model
from keras.layers import Activation, Dense
from keras.layers.recurrent import LSTM
from keras.utils import plot_model
from gensim.models import Word2Vec
from pyltp import Segmentor

from util import eprint, iprint, dprint


def nn():
    model = Sequential()

    model.add(LSTM(300, input_shape=(None, 300)))
    model.add(Dense(28, activation="softmax"))
    # model.add(Activation("softmax"))

    if os.path.isfile("./output/lstm_resume.h5"):
        iprint("Found trained model, resume training")
        model = load_model("./output/lstm_resume.h5")

    model.compile(loss='categorical_crossentropy', optimizer='sgd', metrics=['accuracy'])

    return model


def split_dataset():
    q_file = open("./data/C_train_Q_split_vec.dat", "rb")

    train_file = open("./data/train.dat", "wb")
    test_file = open("./data/test.dat", "wb")

    percent_of_train = 0.8

    while True:
        try:
            item = cPickle.load(q_file)
            if random.random() < percent_of_train:
                cPickle.dump(item, train_file, protocol=cPickle.HIGHEST_PROTOCOL)
            else:
                cPickle.dump(item, test_file, protocol=cPickle.HIGHEST_PROTOCOL)
        except EOFError:
            break

    train_file.close()
    test_file.close()


class MyInput(object):
    i_file = open("./data/img_train_vec.json")
    i_json = json.load(i_file)
    i_file.close()

    def __init__(self, size, input_file):
        self.size = size
        self.input_file = input_file
        self.eof = False

    def __iter__(self):
        while not self.eof:
            xs = []
            ys = []

            for rep in range(self.size):
                try:
                    item = cPickle.load(self.input_file)
                except EOFError:
                    self.eof = True
                    break

                img_key = item["image_filename"]
                try:
                    img = MyInput.i_json[img_key]
                except KeyError:
                    eprint("Image not found", img_key)
                    rep -= 1
                    continue
                img_v = np.repeat(img, 5)
                x = np.empty((1, 300))
                x[0] = img_v

                question_vec = item["C_question_vec"]
                x = np.append(x, question_vec, axis=0)

                max_len = 50
                if len(x) > max_len:
                    eprint("Question too long", item["C_question"])
                    rep -= 1
                    continue
                for i in range(len(x), max_len):
                    zero = np.zeros((1, 300))
                    x = np.append(x, zero, axis=0)

                xs.append(x)

                answer = item["vec_answer"]
                ys.append(answer)

            if not self.eof:
                xs = np.array(xs)
                ys = np.array(ys)
                iprint("xs vector shape", xs.shape)
                iprint("ys vector shape", ys.shape)
                yield xs, ys


def main():
    # split_dataset()

    model = nn()
    plot_model(model, to_file="./output/lstm.png", show_shapes=True)

    batch_size = 3200

    train_loss = []
    train_acc = []
    test_loss = []
    test_acc = []

    for iteration in range(20):
        train_file = open("./data/train.dat", "rb")
        test_file = open("./data/test.dat", "rb")

        train = MyInput(batch_size, train_file)
        test = MyInput(batch_size, test_file)
        loss_l = []
        acc_l = []
        for xs, ys in train:
            history = model.fit(xs, ys, epochs=1)
            loss = np.average(history.history["loss"])
            acc = np.average(history.history["acc"])
            loss_l.append(loss)
            acc_l.append(acc)
        train_loss.append(loss_l)
        train_acc.append(acc_l)

        loss_l = []
        acc_l = []
        for xs, ys in test:
            loss, acc = model.evaluate(xs, ys)
            loss_l.append(loss)
            acc_l.append(acc)
        test_loss.append(loss_l)
        test_acc.append(acc_l)

        iprint("iteration", iteration)
        iprint(train_loss, train_acc, test_loss, test_acc)
        plt.figure()
        plt.boxplot(train_loss)
        plt.title("train_loss")
        plt.savefig("./output/train_loss.png")
        plt.figure()
        plt.boxplot(train_acc)
        plt.title("train_acc")
        plt.savefig("./output/train_acc.png")
        plt.figure()
        plt.boxplot(test_loss)
        plt.title("test_loss")
        plt.savefig("./output/test_loss.png")
        plt.figure()
        plt.boxplot(test_acc)
        plt.title("test_acc")
        plt.savefig("./output/test_acc.png")

        t = time.localtime(time.time())
        now = str(t[3]) + str(t[4])
        model.save("./output/lstm_iter" + now + ".h5")

        train_file.close()
        test_file.close()

    # for batch in range(train_batch_start, train_batch_end):
        # xs, ys = format_input(batch_size, train_file)

        # if batch % 1000 == 0:
            # model.save("./output/lstm" + str(batch) + ".h5")

    # xtest, ytest = format_input(batch_size, test_file)
    # loss, acc = model.evaluate(xs, ys)


if __name__ == "__main__":
    main()
