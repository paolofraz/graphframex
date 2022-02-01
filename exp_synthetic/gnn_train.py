import os
import torch

import time

import matplotlib
import matplotlib.pyplot as plt
import torch
import torch.nn as nn
from code.utils.gen_utils import from_adj_to_edge_index
from torch.autograd import Variable

import utils.math_utils
import utils.io_utils
from evaluate import *
from gnn_eval import *

####### GNN Training #######
def train_node_classification(model, data, device, args):

    data = data.to(device)

    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)

    val_err = []
    train_err = []

    model.train()
    for epoch in range(args.num_epochs):
        optimizer.zero_grad()

        out = model(data.x, data.edge_index)

        loss = model.loss(out[data.train_mask], data.y[data.train_mask])
        val_loss = model.loss(out[data.val_mask], data.y[data.val_mask])

        if epoch % 10 == 0:
            val_err.append(val_loss.item())
            train_err.append(loss.item())

        loss.backward()
        optimizer.step()

    plt.figure()
    plt.plot(range(args.num_epochs // 10), val_err)
    plt.plot(range(args.num_epochs // 10), train_err)


def train_graph_classification(model, train_dataset, val_dataset, test_dataset, 
    device,
    args,
    mask_nodes=True):
    """Train GNN model.

    Args:
        model ([type]): GNN model
        train_dataset ([type]): [description]
        val_dataset ([type]): [description]
        test_dataset ([type]): [description]
        device ([type]): [description]
        args ([type]): [description]
        same_feat (bool, optional): [description]. Defaults to True.
        writer ([type], optional): [description]. Defaults to None.
        mask_nodes (bool, optional): [description]. Defaults to True.
    """


    optimizer = torch.optim.Adam(
        filter(lambda p: p.requires_grad, model.parameters()), lr=0.001
    )
    iter = 0
    best_val_result = {"epoch": 0, "loss": 0, "acc": 0}
    test_result = {"epoch": 0, "loss": 0, "acc": 0}
    train_accs = []
    train_epochs = []
    best_val_accs = []
    best_val_epochs = []
    test_accs = []
    test_epochs = []
    val_accs = []

    for epoch in range(args.num_epochs):
        begin_time = time.time()
        avg_loss = 0.0
        model.train()
        predictions = []
        print("Epoch: ", epoch)
        for batch_idx, data in enumerate(train_dataset):
            model.zero_grad()
            if batch_idx == 0:
                prev_adjs = data["adj"]
                prev_feats = data["feats"]
                prev_labels = data["label"]
                all_adjs = prev_adjs
                all_feats = prev_feats
                all_labels = prev_labels
            elif batch_idx < 20:
                prev_adjs = data["adj"]
                prev_feats = data["feats"]
                prev_labels = data["label"]
                all_adjs = torch.cat((all_adjs, prev_adjs), dim=0)
                all_feats = torch.cat((all_feats, prev_feats), dim=0)
                all_labels = torch.cat((all_labels, prev_labels), dim=0)
                
            if args.gpu:
                adj = Variable(data["adj"].float(), requires_grad=False).cuda()
                h0 = Variable(data["feats"].float(), requires_grad=False).cuda()
                label = Variable(data["label"].long()).cuda()
                batch_num_nodes = data["num_nodes"].int().numpy() if mask_nodes else None
                assign_input = Variable(
                    data["assign_feats"].float(), requires_grad=False
                ).cuda()
                
            else:
                adj = Variable(data["adj"].float(), requires_grad=False)
                h0 = Variable(data["feats"].float(), requires_grad=False)
                label = Variable(data["label"].long())
                batch_num_nodes = data["num_nodes"].int().numpy() if mask_nodes else None
                assign_input = Variable(
                    data["assign_feats"].float(), requires_grad=False
                )

            edge_index = []
            for a in adj:
                edge_index.append(from_adj_to_edge_index(a))
            
            ypred = model(h0, edge_index, batch_num_nodes, assign_x=assign_input)
            #ypred, att_adj = model(h0, adj, batch_num_nodes, assign_x=assign_input)
            if batch_idx < 5:
                predictions += ypred.cpu().detach().numpy().tolist()

            if not args.method == "soft-assign" or not args.linkpred:
                loss = model.loss(ypred, label)
            else:
                loss = model.loss(ypred, label, adj, batch_num_nodes)
            loss.backward()
            nn.utils.clip_grad_norm(model.parameters(), args.clip)
            optimizer.step()
            iter += 1
            avg_loss += loss

        avg_loss /= batch_idx + 1
        elapsed = time.time() - begin_time
        print("Avg loss: ", avg_loss, "; epoch time: ", elapsed)
        
        result = gnn_scores(train_dataset, model, args, name="Train", max_num_examples=100)
        train_accs.append(result["acc"])
        train_epochs.append(epoch)
        if val_dataset is not None:
            val_result = gnn_scores(val_dataset, model, args, name="Validation")
            val_accs.append(val_result["acc"])
        if val_result["acc"] > best_val_result["acc"] - 1e-7:
            best_val_result["acc"] = val_result["acc"]
            best_val_result["epoch"] = epoch
            best_val_result["loss"] = avg_loss
        if test_dataset is not None:
            test_result = gnn_scores(test_dataset, model, args, name="Test")
            test_result["epoch"] = epoch
        print("Best val result: ", best_val_result)
        best_val_epochs.append(best_val_result["epoch"])
        best_val_accs.append(best_val_result["acc"])
        if test_dataset is not None:
            print("Test result: ", test_result)
            test_epochs.append(test_result["epoch"])
            test_accs.append(test_result["acc"])

    matplotlib.style.use("seaborn")
    plt.switch_backend("agg")
    plt.figure()
    plt.plot(train_epochs, math_utils.exp_moving_avg(train_accs, 0.85), "-", lw=1)
    if test_dataset is not None:
        plt.plot(best_val_epochs, best_val_accs, "bo", test_epochs, test_accs, "go")
        plt.legend(["train", "val", "test"])
    else:
        plt.plot(best_val_epochs, best_val_accs, "bo")
        plt.legend(["train", "val"])
    plt.savefig(io_utils.gen_train_plt_name(args), dpi=600)
    plt.close()
    matplotlib.style.use("default")

    print(all_adjs.shape, all_feats.shape, all_labels.shape)
    return





def save_model(model, args):
    filename = os.path.join(args.save_dir, args.dataset) + "gcn.pth.tar"
    torch.save(
        {
            "model_type": 'gcn',
            "model_state": model.state_dict()
        },
        str(filename),
    )

def load_model(args):
    '''Load a pre-trained pytorch model from checkpoint.
        '''
    print("loading model")
    filename = os.path.join(args.save_dir, args.dataset) + "/gcn.pth.tar"
    print(filename)
    if os.path.isfile(filename):
        print("=> loading checkpoint '{}'".format(filename))
        ckpt = torch.load(filename)
    else:
        print("Checkpoint does not exist!")
        print("Checked path -- {}".format(filename))
        print("Make sure you have provided the correct path!")
        print("You may have forgotten to train a model for this dataset.")
        print()
        print("To train one of the paper's models, run the following")
        print(">> python train_gnn.py --dataset=DATASET_NAME")
        print()
        raise Exception("File not found.")
    return ckpt
