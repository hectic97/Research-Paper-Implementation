# -*- coding: utf-8 -*-
"""ResNet+SENet_CIFAR_10.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1tBkji-hzcoNjvCrLGAUWSBW0o-RQzmYp
"""

import torch
import torchvision
import torch.nn as nn
import torch.nn.init as init
import torch.optim as optim
from torchvision import transforms
import numpy as np
import matplotlib.pyplot as plt
import torch.nn.functional as F

class SENet(nn.Module):
    def __init__(self,channel,reduction):
        super(SENet,self).__init__()
        self.avg_pool = nn.AdaptiveAvgPool2d(1)
        self.dense_1 = nn.Linear(channel,channel//reduction,False)
        self.relu = nn.ReLU()
        self.dense_2 = nn.Linear(channel//reduction,channel,False)
        self.sigmoid = nn.Sigmoid()

    def forward(self,x):
        batch = x.size(0) 
        ch = x.size(1)
        out = self.avg_pool(x)
        out = out.view(batch,ch)
        out = self.dense_1(out)
        out = self.relu(out)
        out = self.dense_2(out)
        out = self.sigmoid(out)
        out = out.view(batch,ch,1,1)
        return x * out.expand(x.size())

def _weights_init(m):
    classname = m.__class__.__name__
    if isinstance(m, nn.Linear) or isinstance(m, nn.Conv2d):
        init.kaiming_normal_(m.weight)

class LambdaLayer(nn.Module):
    def __init__(self, lambd):
        super(LambdaLayer, self).__init__()
        self.lambd = lambd

    def forward(self, x):
        return self.lambd(x)

class LayerBlock(nn.Module):
    def __init__(self,in_dim,out_dim,down=False):
        super(LayerBlock,self).__init__()
  
        self.bn1 = nn.BatchNorm2d(out_dim)  
        self.bn2 = nn.BatchNorm2d(out_dim)
        self.bn3 = nn.BatchNorm2d(out_dim)
        self.relu = nn.ReLU(inplace=True)
        self.conv2 = nn.Conv2d(out_dim,out_dim,3,1,1,bias=False)
        self.down = down
        self.in_dim = in_dim
        self.out_dim =out_dim
        self.match_size = LambdaLayer(lambda x:F.pad(x[:, :, ::2, ::2], (0, 0, 0, 0, out_dim//4, out_dim//4), "constant", 0))
        self.se_layer = nn.Sequential(SENet(self.out_dim,16)) 
        

        if self.down:
            self.conv1 = nn.Conv2d(in_dim,out_dim,3,2,1,bias=False)
            self.layer = nn.Sequential(
                self.conv1,
                self.bn1,
                self.relu,
                self.conv2,
                self.bn2

            )
            
        else:
            self.conv1 = nn.Conv2d(in_dim,out_dim,3,1,1,bias=False)
            self.layer = nn.Sequential(
                self.conv1,
                self.bn1,
                self.relu,
                self.conv2,
                self.bn2

            )
    
    def forward(self,x):
        if self.down:
            down_x = self.match_size(x)
            out = self.layer(x)
            out = self.se_layer(out)
            out = out + down_x
        else:
            out = self.layer(x)

            if not x.size()==out.size():
                x = self.match_size(x)
            
            out = self.se_layer(out)
            out = out+x
        out = self.relu(out)
        return out






class MyResNet(nn.Module):
    def __init__(self):
        super(MyResNet,self).__init__()
        self.conv1 = nn.Conv2d(3,16,3,1,1,bias=False)
        self.bn = nn.BatchNorm2d(16)
        self.relu = nn.ReLU(inplace=True)
        self.layer1 = nn.Sequential(
            LayerBlock(16,16),
            LayerBlock(16,16),
            LayerBlock(16,16),
            LayerBlock(16,16),
            LayerBlock(16,16),
            )
        self.layer2 = nn.Sequential(
            LayerBlock(16,32,True),
            LayerBlock(32,32),
            LayerBlock(32,32),
            LayerBlock(32,32),
            LayerBlock(32,32),
        )
        self.layer3 = nn.Sequential(
            LayerBlock(32,64,True),
            LayerBlock(64,64),
            LayerBlock(64,64),
            LayerBlock(64,64),
            LayerBlock(64,64),
            
        )
        # self.avgpool = nn.AdaptiveAvgPool2d((1,1))
        self.dense = nn.Linear(64,10)
        self.apply(_weights_init)

    def forward(self,x):
        x = self.conv1(x)
        x = self.bn(x)
        x = self.relu(x)
        x = self.layer1(x)
        x = self.layer2(x)
        x = self.layer3(x)
        # x = self.avgpool(x)
        x = F.avg_pool2d(x,x.size()[3])
        x = x.view(x.size()[0],-1)
        x = self.dense(x)

        return x

import torch
import torchvision
import torch.optim as optim
from torchvision import transforms
import numpy as np
import matplotlib.pyplot as plt

batch_size = 128
transform_train = transforms.Compose([
                                      transforms.RandomHorizontalFlip(),
                                      transforms.RandomCrop(32,padding=4),
                                      transforms.ToTensor(),
                                      transforms.Normalize(mean=(0.485,0.456,0.406),std=(0.229,0.224,0.225)),

])
transform_test = transforms.Compose([
                            
                                      transforms.ToTensor(),
                                      transforms.Normalize(mean=(0.485,0.456,0.406),std=(0.229,0.224,0.225)),
                                      
])
train_set = torchvision.datasets.CIFAR10(root='./',train=True,download=True,transform=transform_train)
test_set = torchvision.datasets.CIFAR10(root='./',train=False,download=True,transform=transform_test)

from sklearn.model_selection import train_test_split
targets = train_set.targets
train_idx ,valid_idx = train_test_split(np.arange(len(targets)),test_size=0.1,random_state=517,shuffle=True,stratify=targets)
train_sampler = torch.utils.data.SubsetRandomSampler(train_idx)
valid_sampler = torch.utils.data.SubsetRandomSampler(valid_idx)

train_loader = torch.utils.data.DataLoader(train_set,batch_size = batch_size,sampler=train_sampler,pin_memory=True)
val_loader = torch.utils.data.DataLoader(train_set,batch_size = batch_size,sampler=valid_sampler,pin_memory=True)
test_loader = torch.utils.data.DataLoader(test_set,batch_size=batch_size)
device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
print(device)
model = MyResNet().to(device)
model = nn.DataParallel(model)

loss_func = nn.CrossEntropyLoss()
optimizer = torch.optim.SGD(model.parameters(),lr=0.1,momentum=0.9,weight_decay=1e-4)
lr_scheduler = torch.optim.lr_scheduler.MultiStepLR(optimizer,[100,150])

epochs = 200

for i in range(epochs):
    model.train()
    correct = 0
    total = 0
    for j,[img,label] in enumerate(train_loader):
        x = img.to(device)
        y = label.to(device)

        optimizer.zero_grad()
        output = model.forward(x)
        _,output_index = torch.max(output,1)
        loss = loss_func(output,y)
        loss.backward()
        optimizer.step()
        total += y.size()[0]
        correct += (output_index == y).sum().float()
     
    
    
    
    
    lr_scheduler.step() 
    if i % (epochs/10) == 0:
        with torch.no_grad():
                val_correct = 0
                val_total = 0
                for k,[val_img,val_label] in enumerate(val_loader):
                        val_x = val_img.to(device)
                        val_y = val_label.to(device)
                        model.eval()
                        val_output = model.forward(val_x)
                        _,val_output_index = torch.max(val_output,1)
                        val_loss = loss_func(val_output,val_y)
                        val_total += val_y.size()[0]
                        val_correct += (val_output_index==val_y).sum().float()
        print('EPOCHS {:>3d}/{} | train_loss : {:.4f} | train_acc : {:.4f} | val_loss : {:.4f} | val_acc : {:.4f}'\
                    .format(i+1,epochs,loss,correct*100/total,val_loss,100*val_correct/val_total))

model.eval()
correct = 0
total = 0
with torch.no_grad():
    
    for image,label in test_loader:
        x = image.to(device)
        y = label.to(device)

        output = model.forward(x)
        _,output_index = torch.max(output,1)
        total += label.size(0)
        correct += (output_index == y).sum().float()

    print('Accuracy of Testset : {:.4f}'.format(100*correct/total))
    
# Train Acc : 98.75 %  Test Acc : 92.40 %
