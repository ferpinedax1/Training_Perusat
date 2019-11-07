'''
This is the main code to train

'''
import argparse
from pathlib import Path
import torch
from torch import nn
from torch.optim import Adam
from torch.utils.data import DataLoader
from torchvision import transforms, datasets, models
import torch.backends.cudnn as cudnn
import torch.backends.cudnn
import json
from models import UNet11,UNet, AlbuNet34, SegNet
from dataset import WaterDataset
from torch.optim import lr_scheduler 
import utilsTrain_paral 
import torch.optim as optim
import numpy as np
import glob
import os

from split_train_val import get_files_names
from scalarmeanstd import meanstd
from metrics_prediction import find_metrics
from transformsdata import (DualCompose,
                        ImageOnly,
                        Normalize,
                        Normalize2,
                        HorizontalFlip,
                        Rotate,
                        CenterCrop,
                        VerticalFlip)


def main():
    parser = argparse.ArgumentParser()
    arg = parser.add_argument
    arg('--device-ids', type=str, default='0', help='For example 0,1 to run on two GPUs')
    arg('--root', default='runs/debug', help='checkpoint root')
    arg('--batch-size', type=int, default=4)
    arg('--limit', type=int, default=10000, help='number of images in epoch')
    arg('--n-epochs', type=int, default=40)
    arg('--lr', type=float, default=1e-3)
    arg('--modelHR', type=str, default='UNet11', choices=['UNet11','UNet','AlbuNet34','SegNet'])

    args = parser.parse_args()
    
    root = Path(args.root)
    root.mkdir(exist_ok=True, parents=True)

    num_class = 1
    
    if args.model == 'UNet11':
        model_LR = UNet11(num_class)
        model_HR = UNet11(num_class)
    elif args.model == 'UNet':
        model_LR = UNet(num_classes=num_classes)
        model_HR = UNet(num_classes=num_classes)

    elif args.model == 'AlbuNet34':
        model_LR = AlbuNet34(num_classes=num_classes, num_input_channels=4, pretrained=False)
        model_HR = AlbuNet34(num_classes=num_classes, num_input_channels=4, pretrained=False)
        
    elif args.model == 'SegNet':
        model_LR = SegNet(num_classes=num_classes, num_input_channels=4, pretrained=False)
        model_HR = SegNet(num_classes=num_classes, num_input_channels=4, pretrained=False)

    else:
        model_LR = UNet11(num_classes = num_class, input_channels=4)
        model_HR = UNet11(num_classes = num_class, input_channels=4)
        

        
    if torch.cuda.is_available():
        if args.device_ids:#
            device_ids = list(map(int, args.device_ids.split(',')))
        else:
            device_ids = None
        model_LR = nn.DataParallel(model_LR, device_ids=device_ids).cuda()
        model_HR = nn.DataParallel(model_HR, device_ids=device_ids).cuda()# to run the code in multiple gpus
    #loss = utilsTrain.calc_loss(pred, target, metrics, bce_weight=0.5)#debjani

    cudnn.benchmark = True



    out_path = Path('logs_paral/mapping/')

#Data-paths:--------------------------LR-------------------------------------
    data_path_LR = Path('data_LR') # change the data path here 
    print("data_path:",data_path_LR)
    
    train_path_LR= data_path_LR/'train'/'images'
    val_path_LR= data_path_LR/'val'/'images'

    ###############  Dowscale HR perusat #########
    data_path_LR = Path('data_HR') # change the data path here 
    print("data_path:",data_path_LR)
    
    train_path_LR= data_path_LR/'dist_per'/'train_LR'/'images'
    val_path_LR= data_path_LR/'dist_per'/'val_LR'/'images'
    
    name_file_LR='_LR'

#-------------------------------------------------    
    train_file_LR = np.array(sorted(list(train_path_LR.glob('*.npy'))))
    print(len(train_file_LR))
    val_file_LR = np.array(sorted(list(val_path_LR.glob('*.npy'))))
    print(len(val_file_LR))
    
    #Data-paths:--------------------------HR-------------------------------------
    data_path_HR = Path('data_HR') # change the data path here 
    print("data_path:",data_path_HR)
    #train_path_HR_lab= data_path_HR/'train'/'images'
    #val_path_HR_lab= data_path_HR/'val'/'images'
    
    #train_path_HR_lab= data_path_HR/'train_100'/'images'
    #val_path_HR_lab= data_path_HR/'val_100'/'images'
    
    #train_path_HR_lab= data_path_HR/'train_400'/'images'
    #val_path_HR_lab= data_path_HR/'val_400'/'images'
    
    #train_path_HR_lab= data_path_HR/'dist_per'/'train_HR'/'images'
   #val_path_HR_lab= data_path_HR/'dist_per'/'val_HR'/'images'
    
    #train_path_HR_lab= data_path_HR/'dist_per'/'train_HR_60'/'images'
    #val_path_HR_lab= data_path_HR/'dist_per'/'val_HR_60'/'images'
    name_file_HR='_dist_60_2'


      #Data-paths:--------------------------HR-------------------------------------
    train_file_HR_lab, val_file_HR_lab = get_files_names(data_path_HR,name_file_HR)
         np.save(str(os.path.join(out_path,"train_files{}_{}.npy".format(name_file,args.model))), train_file_HR_lab)
    np.save(str(os.path.join(out_path,"val_files{}_{}.npy".format(name_file_HR,args.model))), val_file_HR_lab)
      

    
    #train_file_HR_lab = np.array(sorted(list(train_path_HR_lab.glob('*.npy'))))
#    print(len(train_file_HR_lab))
#    val_file_HR_lab = np.array(sorted(list(val_path_HR_lab.glob('*.npy'))))
   


        
    train_path_HR_unlab= data_path_HR/'unlabel'/'train'/'images'
    val_path_HR_unlab = data_path_HR/'unlabel'/'val'/'images'
    
    train_file_HR_unlab = np.array(sorted(list(train_path_HR_unlab.glob('*.npy'))))
   
    val_file_HR_unlab = np.array(sorted(list(val_path_HR_unlab.glob('*.npy'))))
    
    print('num train_lab = {}, num_val_lab = {}'.format(len(train_file_HR_lab), len(val_file_HR_lab)))
    print('num train_unlab = {}, num_val_unlab = {}'.format(len(train_file_HR_unlab), len(val_file_HR_unlab)))    #--------------------------------------------------------------------------------------------------------

    #-----------------------------------------------------------------------------------------------------------------
    
        max_values_HR, mean_values_HR, std_values_HR=meanstd(train_file_HR_lab, val_file_HR_lab,name_file_HR,str(data_path_HR)) #_60 --data_HR, data_LR
    
    
    def make_loader(file_names, shuffle=False, transform=None, limit=None,  mode = "train",batch_size = 4,limite=None) :
             return DataLoader(
                dataset=WaterDataset(file_names, transform=transform, mode = mode,limit=limit),
                shuffle=shuffle,
                batch_size= batch_size)
    
    
    #transformations ---------------------------------------------------------------------------                      
    train_transform_HR = DualCompose([
            CenterCrop(512),
            HorizontalFlip(),
            VerticalFlip(),
            Rotate(),
            ImageOnly(Normalize(mean_values_HR, std_values_HR))
        ])
    
    val_transform_HR = DualCompose([
            CenterCrop(512),
            ImageOnly(Normalize(mean_values_HR, std_values_HR))
        ])
    
    
    train_transform_LR = DualCompose([
            #CenterCrop(64),
            CenterCrop(512),#using the  HR normalization fake
            HorizontalFlip(),
            VerticalFlip(),
            Rotate(),
            ImageOnly(Normalize(mean_values_LR, std_values_LR))   #using the  HR normalization
        ])
    
    val_transform_LR = DualCompose([
            #CenterCrop(64),
            CenterCrop(512),#using the  HR normalization fake
            ImageOnly(Normalize(mean_values_LR, std_values_LR))    #using the  HR normalization fake
        ])
    
    
    ######################## DATA-LOADERS ###########################################################
      
    train_loader_HR_lab = make_loader(train_file_HR_lab, shuffle=True, transform=train_transform_HR , batch_size = 4 , mode = "train")
    valid_loader_HR_lab = make_loader(val_file_HR_lab, transform=val_transform_HR, batch_size = 4, mode = "train")
    
    train_loader_HR_unlab = make_loader(train_file_HR_unlab, shuffle=True, transform=train_transform_HR, batch_size = 2, mode = "unlb_train")
    valid_loader_HR_unlab = make_loader(val_file_HR_unlab, transform=val_transform_HR, batch_size = 2, mode = "unlb_val")
 
   # train_loader_HR_lab = make_loader(train_file_HR_lab, shuffle=False, transform=train_transform_HR , batch_size = 2 , mode = "train")
   # valid_loader_HR_lab = make_loader(val_file_HR_lab, transform=val_transform_HR, batch_size = 2, mode = "train")
    
  #  train_loader_HR_unlab = make_loader(train_file_HR_lab, shuffle=False, transform=train_transform_HR , batch_size = 2 , mode = "train")
  #  valid_loader_HR_unlab = make_loader(val_file_HR_lab, transform=val_transform_HR, batch_size = 2, mode = "train")
               ############# images fakes de 8 a 4 bacth size
    train_loader_LR = make_loader(train_file_LR, shuffle=True, transform=train_transform_LR, batch_size = 4, mode = "train" )
    valid_loader_LR = make_loader(val_file_LR, transform=val_transform_LR, batch_size = 4, mode = "train")
    print(train_path_HR_lab)
        
        
    dataloaders_HR_lab= {
        'train': train_loader_HR_lab, 'val': valid_loader_HR_lab
    }
    
    dataloaders_HR_unlab= {
        'train': train_loader_HR_unlab, 'val': valid_loader_HR_unlab
    }
    
    dataloaders_LR= {
        'train': train_loader_LR, 'val': valid_loader_LR
    }
    
    #PRINT THE SIZES----------------------------------------------
    dataloaders_sizes = {
        x: len(dataloaders_HR_lab[x]) for x in dataloaders_HR_lab.keys()
        
    }
    print('HR',dataloaders_sizes)
    
    dataloaders_sizes = {
        x: len(dataloaders_LR[x]) for x in dataloaders_LR.keys()
    }
    print('LR',dataloaders_sizes)

    #----------------------------------------------------------------------------------------------
    root.joinpath('params_paral.json').write_text(
        json.dumps(vars(args), indent=True, sort_keys=True))
    
    # Observe that all parameters are being optimized
    optimizer_ft = optim.Adam(list(model_LR.parameters()) + list(model_HR.parameters()), lr=args.lr)

    exp_lr_scheduler = lr_scheduler.StepLR(optimizer_ft, step_size=20, gamma=0.1) #debjani
    
    utilsTrain.train_model(name_file_HR,
                           model_LR, model_HR, 
                           optimizer_ft,                                        exp_lr_scheduler,
                           dataloaders_HR_lab,
                           dataloaders_HR_unlab,
                           dataloaders_LR,
                           args.modelHR,

                           #183, num_epochs = 40) #733  batch de 4
                           #25, num_epochs = 40) #90
                           #100, num_epochs = 40) #400
                           15, args.n_epochs) #60

    #torch.save(model_LR.module.state_dict(), out_path/'LR_model_temp2.pth')
    #torch.save(model_HR.module.state_dict(), out_path/'HR_model_temp2.pth')
 
    #torch.save(model_LR.module.state_dict(), out_path/'LR_model_temp_100.pth')
    #torch.save(model_HR.module.state_dict(), out_path/'HR_model_temp2_100.pth')
    
    #torch.save(model_LR.module.state_dict(), out_path/'LR_model_temp_400.pth')
    #torch.save(model_HR.module.state_dict(), out_path/'HR_model_temp2_400.pth')
        
    #torch.save(model_LR.module.state_dict(), out_path/'LR_model_fake.pth')
    #torch.save(model_HR.module.state_dict(), out_path/'HR_model_fake.pth')
    
    torch.save(model_LR.module.state_dict(), (str(out_path)+'/model_40epoch{}_{}.pth').format(name_file_LR,args.model))
    torch.save(model_HR.module.state_dict(), (str(out_path)+'/model_40epoch{}_{}.pth').format(name_file_HR,args.model))
    
    print(args.model)
    find_metrics(train_file_HR_lab, val_file_HR_lab, max_values_HR, mean_values_HR, std_values_HR,args.model, out_file='paral', dataset_file='HR',name_file=name_file_HR)
    
if __name__ == '__main__':
    main()