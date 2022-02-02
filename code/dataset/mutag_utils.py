import random

import networkx as nx
import numpy as np
import torch
import torch.utils.data
from torch.autograd import Variable
from torch_geometric.utils.convert import to_networkx
from utils.gen_utils import get_test_graphs


class GraphSampler(torch.utils.data.Dataset):
    """Sample graphs and nodes in graph"""

    def __init__(
        self,
        G_list,
        features="default",
        normalize=True,
        assign_feat="default",
        max_num_nodes=0,
    ):
        self.adj_all = []
        self.len_all = []
        self.feature_all = []
        self.label_all = []

        self.assign_feat_all = []

        if max_num_nodes == 0:
            self.max_num_nodes = max([G.number_of_nodes() for G in G_list])
        else:
            self.max_num_nodes = max_num_nodes

        existing_node = list(G_list[0].nodes())[-1]
        self.feat_dim = G_list[0].nodes[existing_node]["feat"].shape[0]

        for G in G_list:
            adj = np.array(nx.to_numpy_matrix(G))
            if normalize:
                sqrt_deg = np.diag(1.0 / np.sqrt(np.sum(adj, axis=0, dtype=float).squeeze()))
                adj = np.matmul(np.matmul(sqrt_deg, adj), sqrt_deg)
            self.adj_all.append(adj)
            self.len_all.append(G.number_of_nodes())
            self.label_all.append(G.graph["label"])
            # feat matrix: max_num_nodes x feat_dim
            if features == "default":
                f = np.zeros((self.max_num_nodes, self.feat_dim), dtype=float)
                for i, u in enumerate(G.nodes()):
                    f[i, :] = G.nodes[u]["feat"]
                self.feature_all.append(f)
            elif features == "id":
                self.feature_all.append(np.identity(self.max_num_nodes))
            elif features == "deg-num":
                degs = np.sum(np.array(adj), 1)
                degs = np.expand_dims(
                    np.pad(degs, [0, self.max_num_nodes - G.number_of_nodes()], 0),
                    axis=1,
                )
                self.feature_all.append(degs)
            elif features == "deg":
                self.max_deg = 10
                degs = np.sum(np.array(adj), 1).astype(int)
                degs[degs > self.max_deg] = self.max_deg
                feat = np.zeros((len(degs), self.max_deg + 1))
                feat[np.arange(len(degs)), degs] = 1
                feat = np.pad(
                    feat,
                    ((0, self.max_num_nodes - G.number_of_nodes()), (0, 0)),
                    "constant",
                    constant_values=0,
                )

                f = np.zeros((self.max_num_nodes, self.feat_dim), dtype=float)
                for i, u in enumerate(G.nodes()):
                    f[i, :] = G.nodes[u]["feat"]

                feat = np.concatenate((feat, f), axis=1)

                self.feature_all.append(feat)
            elif features == "struct":
                self.max_deg = 10
                degs = np.sum(np.array(adj), 1).astype(int)
                degs[degs > 10] = 10
                feat = np.zeros((len(degs), self.max_deg + 1))
                feat[np.arange(len(degs)), degs] = 1
                degs = np.pad(
                    feat,
                    ((0, self.max_num_nodes - G.number_of_nodes()), (0, 0)),
                    "constant",
                    constant_values=0,
                )

                clusterings = np.array(list(nx.clustering(G).values()))
                clusterings = np.expand_dims(
                    np.pad(
                        clusterings,
                        [0, self.max_num_nodes - G.number_of_nodes()],
                        "constant",
                    ),
                    axis=1,
                )
                g_feat = np.hstack([degs, clusterings])
                if "feat" in G.nodes[0]:
                    node_feats = np.array([G.nodes[i]["feat"] for i in range(G.number_of_nodes())])
                    node_feats = np.pad(
                        node_feats,
                        ((0, self.max_num_nodes - G.number_of_nodes()), (0, 0)),
                        "constant",
                    )
                    g_feat = np.hstack([g_feat, node_feats])

                self.feature_all.append(g_feat)

            if assign_feat == "id":
                self.assign_feat_all.append(np.hstack((np.identity(self.max_num_nodes), self.feature_all[-1])))
            else:
                self.assign_feat_all.append(self.feature_all[-1])

        self.feat_dim = self.feature_all[0].shape[1]
        self.assign_feat_dim = self.assign_feat_all[0].shape[1]

    def __len__(self):
        return len(self.adj_all)

    def __getitem__(self, idx):
        adj = self.adj_all[idx]
        num_nodes = adj.shape[0]
        adj_padded = np.zeros((self.max_num_nodes, self.max_num_nodes))
        adj_padded[:num_nodes, :num_nodes] = adj

        # use all nodes for aggregation (baseline)
        return {
            "adj": adj_padded,
            "feats": self.feature_all[idx].copy(),
            "label": self.label_all[idx],
            "num_nodes": num_nodes,
            "assign_feats": self.assign_feat_all[idx].copy(),
        }


def neighborhoods(adj, n_hops, use_cuda):
    """Returns the n_hops degree adjacency matrix adj."""
    adj = torch.tensor(adj, dtype=torch.float)
    if use_cuda:
        adj = adj.cuda()
    hop_adj = power_adj = adj
    for i in range(n_hops - 1):
        power_adj = power_adj @ adj
        prev_hop_adj = hop_adj
        hop_adj = hop_adj + power_adj
        hop_adj = (hop_adj > 0).float()
    return hop_adj.cpu().numpy().astype(int)


def prepare_data(graphs, args, test_graphs=None, max_nodes=0):

    random.shuffle(graphs)
    if test_graphs is None:
        train_idx = int(len(graphs) * args.train_ratio)
        test_idx = int(len(graphs) * (1 - args.test_ratio))
        train_graphs = graphs[:train_idx]
        val_graphs = graphs[train_idx:test_idx]
        test_graphs = graphs[test_idx:]
    else:
        train_idx = int(len(graphs) * args.train_ratio)
        train_graphs = graphs[:train_idx]
        val_graphs = graphs[train_idx:]
    print(
        "Num training graphs: ",
        len(train_graphs),
        "; Num validation graphs: ",
        len(val_graphs),
        "; Num testing graphs: ",
        len(test_graphs),
    )

    print("Number of graphs: ", len(graphs))
    print("Number of edges: ", sum([G.number_of_edges() for G in graphs]))
    print(
        "Max, avg, std of graph size: ",
        max([G.number_of_nodes() for G in graphs]),
        ", " "{0:.2f}".format(np.mean([G.number_of_nodes() for G in graphs])),
        ", " "{0:.2f}".format(np.std([G.number_of_nodes() for G in graphs])),
    )

    # minibatch
    dataset_sampler = GraphSampler(
        train_graphs,
        normalize=False,
        max_num_nodes=max_nodes,
        features=args.feature_type,
    )
    train_dataset_loader = torch.utils.data.DataLoader(
        dataset_sampler,
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=args.num_workers,
    )

    dataset_sampler = GraphSampler(val_graphs, normalize=False, max_num_nodes=max_nodes, features=args.feature_type)
    val_dataset_loader = torch.utils.data.DataLoader(
        dataset_sampler,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=args.num_workers,
    )

    dataset_sampler = GraphSampler(
        test_graphs,
        normalize=False,
        max_num_nodes=max_nodes,
        features=args.feature_type,
    )
    test_dataset_loader = torch.utils.data.DataLoader(
        dataset_sampler,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=args.num_workers,
    )

    return (
        train_dataset_loader,
        val_dataset_loader,
        test_dataset_loader,
        dataset_sampler.max_num_nodes,
        dataset_sampler.feat_dim,
        dataset_sampler.assign_feat_dim,
    )


def gen_dataloader(data, args, max_nodes=0):
    graphs = data_to_graph(data)
    list_test_graphs = get_test_graphs(graphs, args)
    dataset_sampler = GraphSampler(
        list_test_graphs,
        normalize=False,
        max_num_nodes=max_nodes,
        features=args.feature_type,
    )
    dataset_loader = torch.utils.data.DataLoader(
        dataset_sampler,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=args.num_workers,
    )
    return dataset_loader


def data_to_graph(data_list):
    graphs = []
    for data in data_list:
        data.feat = np.array(data.x)
        g = to_networkx(data, node_attrs=["feat"])
        g.graph["label"] = np.array(data.y)
        graphs.append(g)
    return graphs
