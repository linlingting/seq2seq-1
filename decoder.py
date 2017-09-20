import tensorflow as tf
from tensorflow.python.layers.core import Dense

class Decoder:
    def __init__(self, hidden_units, num_layers, dropout, max_decode_len, vocab_size, mode='train', eos_token=0):
        self.hidden_units = hidden_units
        self.num_layers = num_layers
        self.dropout = dropout
        self.max_decode_len = max_decode_len
        self.mode = mode
        self.eos_token = eos_token
        self.vocab_size = vocab_size

        self.init_variables()

    def init_variables(self):
        with tf.variable_scope("decoder"):
            if self.mode == 'train':
                self.decoder_sequence_lens = tf.placeholder(tf.int32, shape=(None,), name='sequence_lengths')
                self.decoder_inputs = tf.placeholder(tf.int32, shape=(None, None), name='input_sequences')

            self.cell = tf.nn.rnn_cell.LSTMCell(num_units=self.hidden_units)
            if self.dropout is not None:
                self.cell = tf.nn.rnn_cell.DropoutWrapper(self.cell, input_keep_prob=(1.0 - self.dropout),
                                                              output_keep_prob=(1.0 - self.dropout))

            self.decoder_cell = tf.nn.rnn_cell.MultiRNNCell([self.cell] * self.num_layers)
            self.decoder_output_layer = Dense(self.vocab_size, name='output_projection')

    def forward(self, encoder_states, encoder_sequence_lens, embedding, vocab_size):
        batch_size = tf.shape(encoder_states)[0]

        if self.mode == 'train':
            eos_step = tf.ones(shape=[batch_size, 1], dtype=tf.int32) * self.eos_token

            decoder_train_inputs = tf.concat([eos_step, self.decoder_inputs], axis=1)
            decoder_train_targets = tf.concat([self.decoder_inputs, eos_step], axis=1)

            decoder_sequence_lens_train = self.decoder_sequence_lens + 1

            with tf.variable_scope('decoder', initializer=tf.random_uniform_initializer(-0.1, 0.1)):

                decoder_inputs_embedded = tf.nn.embedding_lookup(embedding, decoder_train_inputs)

                training_helper = tf.contrib.seq2seq.TrainingHelper(inputs=decoder_inputs_embedded,
                                                                    sequence_length=decoder_sequence_lens_train,
                                                                    name='training_helper')

                basic_train_decoder = tf.contrib.seq2seq.BasicDecoder(cell=self.decoder_cell,
                                                                      helper=training_helper,
                                                                      initial_state=encoder_states,
                                                                      output_layer=self.decoder_output_layer)

                max_len = tf.reduce_max(decoder_sequence_lens_train)

                decoder_outputs_train, decoder_states_train, decoder_output_lens_train = tf.contrib.seq2seq.dynamic_decode(
                    decoder=basic_train_decoder,
                    impute_finished=True,
                    maximum_iterations=max_len)

                decoder_output_logits = tf.identity(decoder_outputs_train.rnn_output)

                sequence_masks = tf.sequence_mask(lengths=decoder_sequence_lens_train, maxlen=max_len, dtype=tf.float32,
                                                  name='masks')

                loss = tf.contrib.seq2seq.sequence_loss(logits=decoder_output_logits,
                                                        targets=decoder_train_targets,
                                                        weights=sequence_masks)

                return loss