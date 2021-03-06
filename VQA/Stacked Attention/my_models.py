# -*- coding: utf-8 -*-
"""
Created on Tue May 08 19:06:33 2018

author: Akshita Gupta
"""
from keras.models import Sequential
from keras.layers.core import Reshape, Activation, Dropout
from keras.layers import Input, Dense, Embedding, Conv2D, MaxPool2D
from keras.layers import Flatten, Concatenate
from keras.layers import LSTM, Merge,Bidirectional, RepeatVector, Add, Lambda, Permute
from keras.models import Model
from keras.layers import merge
from keras.applications.vgg19 import VGG19, preprocess_input
from keras import backend as k


def san_atten(common_word_emb_dim,img_vec_dim, activation_1,activation_2, dropout, vocabulary_size,
                num_hidden_units_lstm, max_ques_length,
                word_emb_dim, num_hidden_layers_mlp,
                num_hidden_units_mlp, nb_classes, class_activation,filter_sizes,num_attention_layers):
    
    # Image model
    input_tensor = Input(shape=(448,448,3))
    base_model = VGG19(weights='imagenet', include_top=False, input_tensor=input_tensor)
    inpx1=base_model.get_layer('block5_pool').output
    #in case gpu cannot train big model, make trainable=false and freeze buty some layers
    #according to the results
#    x1=Flatten()(inpx1)
    x1=Dense(common_word_emb_dim, activation='tanh')(inpx1)
    x1=Reshape((-1,196,512))(x1)
    score=Dropout(0.5)(x1)
    image_model = Model([input_tensor],score)
    image_model.summary()
    
    # [1] Recurrent (LSTM) question Model
    inpx0=Input(shape=(max_ques_length,))
    emb0=Embedding(vocabulary_size, word_emb_dim,trainable=False)(inpx0)
	#emb0=Embedding(vocabulary_size, word_emb_dim, weights=[embedding_matrix], trainable=False)(inpx0)
    x1=LSTM(num_hidden_units_lstm, return_sequences=True)(emb0)
    x1=LSTM(num_hidden_units_lstm, return_sequences=False)(x1)
    x2=Dropout(dropout)(x1)    
    x2=Dense(common_word_emb_dim,activation='tanh')(x2)
    question_model = Model([inpx0],x2)
    question_model.summary()
    
    # [2] CNN question model
#    inpx_0=Input(shape=(max_ques_length,))
#    
#    x0=Embedding(vocabulary_size, word_emb_dim, weights=[embedding_matrix], trainable=False)(inpx_0)
#    
#    conv_0 = Conv2D(100, kernel_size=(filter_sizes[0], word_emb_dim), padding='valid', kernel_initializer='normal', activation='relu')(x0)
#    conv_1 = Conv2D(100, kernel_size=(filter_sizes[1], word_emb_dim), padding='valid', kernel_initializer='normal', activation='relu')(x0)
#    conv_2 = Conv2D(100, kernel_size=(filter_sizes[2], word_emb_dim), padding='valid', kernel_initializer='normal', activation='relu')(x0)
#    
#    maxpool_0 = MaxPool2D(pool_size=(max_ques_length - filter_sizes[0] + 1, 1), strides=(1,1), padding='valid')(conv_0)
#    maxpool_1 = MaxPool2D(pool_size=(max_ques_length - filter_sizes[1] + 1, 1), strides=(1,1), padding='valid')(conv_1)
#    maxpool_2 = MaxPool2D(pool_size=(max_ques_length - filter_sizes[2] + 1, 1), strides=(1,1), padding='valid')(conv_2)
#    
#    concatenated_tensor = Concatenate(axis=1)([maxpool_0, maxpool_1, maxpool_2])
#    flatten = Flatten()(concatenated_tensor)
#    dropout = Dropout(0.5)(flatten)
#    output = Dense(common_word_emb_dim,activation='tanh')(dropout)
#    print (output.shape)
#    # this creates a model that includes
#    model = Model(inputs=[inpx_0], outputs=output)
#    model.summary()
        
        
    # Stacked Attention Model
    u= inpx0
    #for 
    img_common=Reshape((-1,512))(score)
    x1=Dense(common_word_emb_dim, activation='tanh')(img_common)
    x1=Reshape((-1,196,512))(x1)
    
    #ques_common=Dense(common_word_emb_dim, activation='tanh')(emb0)
    ques_common=Dense(common_word_emb_dim)(u)
    ques_repl=RepeatVector((196))(ques_common)
    
    img_ques_common=Add()([x1,ques_repl])
    img_ques_common= Activation('tanh')(img_ques_common)
    img_ques_common=Dropout(dropout)(img_ques_common)

    h=Reshape((-1,common_word_emb_dim))(img_ques_common)
    h=Dense(common_word_emb_dim,activation='softmax')(h)
    print(h._keras_shape)
    p=Reshape((196,-1))(h)
#    p=k.transpose(p)
    print(p._keras_shape)
    
    #Weighted sum of image features  
    #nn.View(1, -1):setNumInputDims(1) -> 1*196*512
    p_att=Reshape((1,-1,512))(p)
    print(p_att._keras_shape)
    
    print(score._keras_shape)
    # nn.MM(false, false)({p_att, img_tr}) -> Dot product 
    img_tr_att= (Lambda(lambda x : k.batch_dot(p_att, score,  axes=(1, 1))))(p_att)
    print (img_tr_att._keras_shape)
    # and then transpose after the result
    img_tr_att=Permute((3,2,1))(img_tr_att)
    print (img_tr_att._keras_shape)

    img_tr_att_feat= Reshape((-1,common_word_emb_dim))(img_tr_att)
    print(img_tr_att_feat._keras_shape)
    print(u._keras_shape)
    u=Add()([img_tr_att_feat,x2]) #Add image feature vector and question vector
    o=Dropout(dropout)(u)
    o=Dense(common_word_emb_dim,activation='softmax')(o)
    o=Flatten()(o)
    o=Dense(nb_classes,activation='softmax')(o)

    attention_model=Model([input_tensor,inpx0],o)
    attention_model.summary()

#    model = Sequential()
#    model.add(Merge([attention_model,question_model],mode = 'dd'))
#    model.summary()
#    
    return attention_model
