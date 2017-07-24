import tensorflow as tf
from gemm_op import xnor_gemm


# hard sigmoid -- eq.(3) in Courbariaux et al.

# def binary_sigmoid_unit(x):
#    return hard_sigmoid(x)

'''
# Activation binarization function
def SignTheano(x):
    return tf.subtract(tf.multiply(tf.cast(tf.greater_equal(x, tf.zeros(tf.shape(x))), tf.float32), 2.0), 1.0)
'''


@tf.RegisterGradient("QuantizeGrad")
def quantize_grad(op, grad):
    return tf.clip_by_value(tf.identity(grad), 0, 1)


class BinaryNet:

    def __init__(self, binary, fast, n_hidden, x):
        self.binary = binary
        self.fast = fast
        self.n_hidden = n_hidden
        self.input = x
        self.G = tf.get_default_graph()
        self.dense_layers()

    def init_layer(self, name, n_inputs, n_outputs):

        W = tf.get_variable(name, shape=[
                            n_inputs, n_outputs], initializer=tf.contrib.layers.xavier_initializer())
        #b = tf.Variable(tf.zeros([n_outputs]))
        return W

    def hard_sigmoid(self, x):
        return tf.clip_by_value((x + 1.) / 2, 0, 1)

    def binary_tanh_unit(self, x):
        return 2 * self.hard_sigmoid(x) - 1
    '''
    def binarize(self, W):

        # [-1,1] -> [0,1]
        #Wb = tf.round(self.hard_sigmoid(W))
        Wb = self.hard_sigmoid(W)
        plus_one = tf.ones_like(Wb)
        neg_one = -1 * tf.ones_like(Wb)
        # 0 or 1 -> -1 or 1
        Wb = tf.cast(tf.where(tf.cast(Wb, tf.bool), plus_one, neg_one), tf.float32)
        return Wb            
    '''

    def quantize(self, x):
        with self.G.gradient_override_map({"Sign": "QuantizeGrad"}):
            return tf.sign(x)
            #E = tf.reduce_mean(tf.abs(x))
            # return tf.sign(x) * E

    def dense_layers(self):

        if self.binary:

            with tf.name_scope('fc1_1b') as scope:

                W_1 = self.init_layer('W_1', 784, self.n_hidden)
                fc_1 = self.quantize(self.binary_tanh_unit(
                    tf.matmul(self.input, self.quantize(W_1))))

            with tf.name_scope('fc2_1b') as scope:

                W_2 = self.init_layer('W_2', self.n_hidden, self.n_hidden)
                if self.fast:
                    fc_2 = self.quantize(self.binary_tanh_unit(
                        xnor_gemm(fc_1, self.quantize(W_2))))
                else:
                    fc_2 = self.quantize(self.binary_tanh_unit(
                        tf.matmul(fc_1, self.quantize(W_2))))

            with tf.name_scope('fc3_1b') as scope:

                W_3 = self.init_layer('W_3', self.n_hidden, 10)
                self.output = tf.matmul(fc_2, self.quantize(W_3))
        else:

            with tf.name_scope('fc1_fp') as scope:

                W_1 = self.init_layer('W_1', 784, self.n_hidden)
                fc_1 = tf.nn.relu(tf.matmul(self.input, W_1))

            with tf.name_scope('fc2_fp') as scope:

                W_2 = self.init_layer('W_2', self.n_hidden, self.n_hidden)
                fc_2 = tf.nn.relu(tf.matmul(fc_1, W_2))

            with tf.name_scope('fc3_fp') as scope:

                W_3 = self.init_layer('W_3', self.n_hidden, 10)
                self.output = tf.matmul(fc_2, W_3)
