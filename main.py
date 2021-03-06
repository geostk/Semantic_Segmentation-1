import os.path
import tensorflow as tf
import helper
import warnings
from distutils.version import LooseVersion
import project_tests as tests
import time

# Check TensorFlow Version
assert LooseVersion(tf.__version__) >= LooseVersion('1.0'), 'Please use TensorFlow version 1.0 or newer.  You are using {}'.format(tf.__version__)
print('TensorFlow Version: {}'.format(tf.__version__))

# Check for a GPU
if not tf.test.gpu_device_name():
    warnings.warn('No GPU found. Please use a GPU to train your neural network.')
else:
    print('Default GPU Device: {}'.format(tf.test.gpu_device_name()))


def load_vgg(sess, vgg_path):
    """
    Load Pretrained VGG Model into TensorFlow.
    :param sess: TensorFlow Session
    :param vgg_path: Path to vgg folder, containing "variables/" and "saved_model.pb"
    :return: Tuple of Tensors from VGG model (image_input, keep_prob, layer3_out, layer4_out, layer7_out)
    """
    #   Use tf.saved_model.loader.load to load the model and weights
    vgg_tag = 'vgg16'
    vgg_input_tensor_name = 'image_input:0'
    vgg_keep_prob_tensor_name = 'keep_prob:0'
    vgg_layer3_out_tensor_name = 'layer3_out:0'
    vgg_layer4_out_tensor_name = 'layer4_out:0'
    vgg_layer7_out_tensor_name = 'layer7_out:0'

    tf.saved_model.loader.load(sess, [vgg_tag] , vgg_path)

    graph = tf.get_default_graph()

    tensor_vgg_input = graph.get_tensor_by_name(vgg_input_tensor_name)
    tensor_vgg_keep_prob = graph.get_tensor_by_name(vgg_keep_prob_tensor_name)
    tensor_vgg_layer3_out = graph.get_tensor_by_name(vgg_layer3_out_tensor_name)
    tensor_vgg_layer4_out = graph.get_tensor_by_name(vgg_layer4_out_tensor_name)
    tensor_vgg_layer7_out = graph.get_tensor_by_name(vgg_layer7_out_tensor_name) 

    
    return tensor_vgg_input, tensor_vgg_keep_prob, tensor_vgg_layer3_out, tensor_vgg_layer4_out, tensor_vgg_layer7_out

print ("Test VGG load function")
tests.test_load_vgg(load_vgg, tf)


def layers(vgg_layer3_out, vgg_layer4_out, vgg_layer7_out, num_classes):
    """
    Create the layers for a fully convolutional network.  Build skip-layers using the vgg layers.
    :param vgg_layer7_out: TF Tensor for VGG Layer 3 output
    :param vgg_layer4_out: TF Tensor for VGG Layer 4 output
    :param vgg_layer3_out: TF Tensor for VGG Layer 7 output
    :param num_classes: Number of classes to classify
    :return: The Tensor for the last layer of output
    """
    
    tf.Print(vgg_layer3_out, [tf.shape(vgg_layer3_out[1:3])], message = "Shape of layer3_out = ")
    tf.Print(vgg_layer4_out, [tf.shape(vgg_layer4_out[1:3])], message = "Shape of layer4_out = ")
    tf.Print(vgg_layer7_out, [tf.shape(vgg_layer7_out[1:3])], message = "Shape of layer7_out = ")

    kernel_regularisation = tf.contrib.layers.l2_regularizer(1e-3)

    vgg_layer3_out_scaled = tf.multiply(vgg_layer3_out, 0.0001, name = 'vgg_layer3_out_scaled')
    vgg_layer4_out_scaled = tf.multiply(vgg_layer4_out, 0.01, name = 'vgg_layer4_out_scaled')

    #1x1 conv for the layer7 output
    new_layer7_1x1_out = tf.layers.conv2d(vgg_layer7_out, filters = num_classes, kernel_size = (1,1), strides = (1,1),
        name = 'new_layer7_1x1_out', kernel_initializer = tf.truncated_normal_initializer(stddev = 0.001),
        kernel_regularizer = kernel_regularisation)
    tf.Print(new_layer7_1x1_out, [tf.shape(new_layer7_1x1_out[1:3])], message = "Shape of new_layer7_1x1_out = ")


    new_layer7_1x1_out_upsampled = tf.layers.conv2d_transpose(new_layer7_1x1_out, filters = num_classes, kernel_size = (3,3),
        strides = (2,2), name = 'new_layer7_1x1_out_upsampled', padding = 'same', 
        kernel_regularizer = kernel_regularisation, 
        kernel_initializer = tf.truncated_normal_initializer(stddev = 0.001))
    tf.Print(new_layer7_1x1_out_upsampled, [tf.shape(new_layer7_1x1_out_upsampled[1:3])], 
        message = "Shape of new_layer7_1x1_out_upsampled = ")

    #1x1 conv2d for layer4 output
    new_layer4_1x1_out = tf.layers.conv2d(vgg_layer4_out_scaled, filters = num_classes, kernel_size = (1,1), strides = (1,1),
        name = 'new_layer4_1x1_out', kernel_initializer = tf.truncated_normal_initializer(stddev = 0.001),
        kernel_regularizer = kernel_regularisation)
    tf.Print(new_layer4_1x1_out, [tf.shape(new_layer4_1x1_out[1:3])], message = "Shape of new_layer4_1x1_out = ")

    #combin layer 4 and 7
    new_layer47_combined = tf.add(new_layer4_1x1_out, new_layer7_1x1_out_upsampled, name = 'new_layer47_combined')
    tf.Print(new_layer47_combined, [tf.shape(new_layer47_combined[1:3])], message = "Shape of new_layer47_combined = ")

    #upsample combined layer 4 and 7
    new_layer47_combined_upsampled = tf.layers.conv2d_transpose(new_layer47_combined, filters = num_classes, 
        kernel_size = (3,3), strides = (2,2), name = 'new_layer47_combined_upsampled', padding = 'same', 
        kernel_regularizer = kernel_regularisation, 
        kernel_initializer = tf.truncated_normal_initializer(stddev = 0.001))
    tf.Print(new_layer47_combined_upsampled, [tf.shape(new_layer47_combined_upsampled[1:3])],
     message = "Shape of new_layer47_combined_upsampled = ")


    new_layer3_1x1_out = tf.layers.conv2d(vgg_layer3_out_scaled, filters = num_classes, kernel_size = (1,1), strides = (1,1),
        kernel_regularizer = kernel_regularisation,
        name = 'new_layer3_1x1_out', kernel_initializer = tf.truncated_normal_initializer(stddev = 0.001))
    tf.Print(new_layer3_1x1_out, [tf.shape(new_layer3_1x1_out[1:3])], message = "Shape of new_layer3_1x1_out = ")

    final = tf.add(new_layer3_1x1_out, new_layer47_combined_upsampled)
    tf.Print(final, [tf.shape(final[1:3])], message = "Shape of final = ")

    final_upsampled_8x = tf.layers.conv2d_transpose(final, filters = num_classes, kernel_size = (16,16), strides = (8,8),
        kernel_initializer = tf.truncated_normal_initializer(stddev = 0.001), name = 'final_upsampled_8x', padding = 'same', 
        kernel_regularizer = kernel_regularisation)

    tf.Print(final_upsampled_8x, [tf.shape(final_upsampled_8x[1:3])], message = "Shape of final_upsampled_8x= ")

    return final_upsampled_8x

print ("Test layers function")
tests.test_layers(layers)


def optimize(nn_last_layer, correct_label, learning_rate, num_classes):
    """
    Build the TensorFLow loss and optimizer operations.
    :param nn_last_layer: TF Tensor of the last layer in the neural network
    :param correct_label: TF Placeholder for the correct label image
    :param learning_rate: TF Placeholder for the learning rate
    :param num_classes: Number of classes to classify
    :return: Tuple of (logits, train_op, cross_entropy_loss)
    """
    logits = tf.reshape(nn_last_layer, (-1, num_classes), name = 'logits')
    correct_label = tf.reshape(correct_label, (-1,num_classes), name = 'correct_label')
    cross_entropy_loss = tf.reduce_mean(tf.nn.softmax_cross_entropy_with_logits(logits = logits, labels = correct_label))

    reg_losses = tf.get_collection(tf.GraphKeys.REGULARIZATION_LOSSES)
    reg_constant = 0.5 # Choose an appropriate one.
    loss = cross_entropy_loss + reg_constant * sum(reg_losses)

    optimizer = tf.train.AdamOptimizer(learning_rate = learning_rate)

    opt = optimizer.minimize(loss)

    return logits, opt, loss

print ("Test Optimize function")
tests.test_optimize(optimize)


def train_nn(sess, epochs, batch_size, get_batches_fn, train_op, cross_entropy_loss, input_image,
             correct_label, keep_prob, learning_rate):
    """
    Train neural network and print out the loss during training.
    :param sess: TF Session
    :param epochs: Number of epochs
    :param batch_size: Batch size
    :param get_batches_fn: Function to get batches of training data.  Call using get_batches_fn(batch_size)
    :param train_op: TF Operation to train the neural network
    :param cross_entropy_loss: TF Tensor for the amount of loss
    :param input_image: TF Placeholder for input images
    :param correct_label: TF Placeholder for label images
    :param keep_prob: TF Placeholder for dropout keep probability
    :param learning_rate: TF Placeholder for learning rate
    """
    #Implement function
    print ("*******************TRAINING MODEL*******************\n")
    sess.run(tf.global_variables_initializer())
    t0 = time.time()
    for i in range(epochs):
        print ("Epoch {}".format(i+1))
        t1 = time.time()
        l = 0
        count  = 0
        for image, label in get_batches_fn(batch_size):
            _, loss = sess.run([train_op, cross_entropy_loss], 
                feed_dict = {input_image: image, correct_label: label,keep_prob: 0.55, learning_rate: 0.0001})
            l += loss
            count += 1 
            print ("Loss = {:.3f}".format(loss))
        t2 = time.time() - t1
        print ("Epoch_{} = {:.2f}s, Avg_Loss = {:.3f}".format(i+1, t2, l/count))
        if i %5 == 0 and i !=0:
            print("********************Saving the model*********************")
            model_save = "saved_model_epoch_" + str(i)
            builder = tf.saved_model.builder.SavedModelBuilder(model_save)
            builder.add_meta_graph_and_variables(sess, ["vgg16_semantic"])
            builder.save()
            print("***********************Model saved***********************")
    print ("Total training time ={:.2f}s".format(time.time() - t0))

print ("Test Training function")              
tests.test_train_nn(train_nn)


def run():
    num_classes = 2
    image_shape = (160, 576)
    data_dir = './data'
    runs_dir = './runs'

    print ("Test for KITTI dataset")
    tests.test_for_kitti_dataset(data_dir)

    # Download pretrained vgg model
    helper.maybe_download_pretrained_vgg(data_dir)

    # OPTIONAL: Train and Inference on the cityscapes dataset instead of the Kitti dataset.
    # You'll need a GPU with at least 10 teraFLOPS to train on.
    #  https://www.cityscapes-dataset.com/

    with tf.Session() as sess:
        # Path to vgg model
        vgg_path = os.path.join(data_dir, 'vgg')
        # Create function to get batches
        get_batches_fn = helper.gen_batch_function(os.path.join(data_dir, 'data_road/training'), image_shape)

        # OPTIONAL: Augment Images for better results
        #  https://datascience.stackexchange.com/questions/5224/how-to-prepare-augment-images-for-neural-network

        # Build NN using load_vgg, layers, and optimize function
        epochs = 30
        batch_size = 2

        correct_labels = tf.placeholder(tf.int32, [None, None, None, num_classes], name = 'correct_labels')
        learning_rate = tf.placeholder(tf.float32, name = 'learning_rate')

        input_image, keep_prob, vgg3 , vgg4 , vgg7 = load_vgg(sess, vgg_path)

        nn_last_layer = layers(vgg3, vgg4,vgg7, num_classes)

        logits, train_op, cross_entropy = optimize(nn_last_layer, correct_labels, learning_rate, num_classes)

        # Train NN using the train_nn function
        train_nn(sess, epochs, batch_size, get_batches_fn, train_op, cross_entropy, input_image,
             correct_labels, keep_prob, learning_rate)        

        print("********************Saving the model*********************")
        model_save = "saved_model_" + str(time.time()) + str(epochs)
        builder = tf.saved_model.builder.SavedModelBuilder(model_save)
        builder.add_meta_graph_and_variables(sess, ["vgg16_semantic"])
        builder.save()
        print("***********************Model saved***********************")
        # Save inference data using helper.save_inference_samples
        helper.save_inference_samples(runs_dir=runs_dir, data_dir=data_dir, sess=sess,image_shape=image_shape,
        logits = logits, keep_prob=keep_prob, input_image=input_image)

        # Apply the trained model to a video


if __name__ == '__main__':
    run()
