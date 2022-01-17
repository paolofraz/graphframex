import numpy as np
import os
from synthetic_structsim import house, grid, cycle, bottle
from explainer import node_attr_to_edge


# Only compares common nodes in the predicted and groundtruth graphs
def evaluate_syn_explanation(explanations, args):
    gt_positive = 0
    true_positive = 0
    pred_positive = 0
    for node in explanations:
        ground_truth = get_ground_truth(node, args)
        gt_positive = gt_positive + len(ground_truth)
        pred_positive = pred_positive + len(explanations[node])
        for ex_node in explanations[node]:
            if ex_node in ground_truth:
                true_positive = true_positive + 1

    accuracy = true_positive / gt_positive
    precision = true_positive / pred_positive

    print("Accuracy: ", accuracy)
    print("Precision: ", precision)

    savedir = 'result/'
    if args.top_node == None:
        top = "no_top"
    else:
        top = "top_" + str(args.top_node)
    report_file_name = 'report_' + args.dataset + ".txt"
    report_file = os.path.join(savedir, report_file_name)

    with open(report_file, "a") as text_file:
        text_file.write(
            prog_args.dataset + ", " + str(prog_args.num_perturb_samples) + " samples, " + top + " | Accuracy: " + str(
                accuracy) + "\n")
        text_file.write(
            prog_args.dataset + ", " + str(prog_args.num_perturb_samples) + " samples, " + top + " | Precision: " + str(
                precision) + "\n")
        text_file.write("\n")


def get_ground_truth(node, data, args):
    gt = []
    if args.dataset == 'syn1':
        gt = get_ground_truth_syn1(node)  # correct
        graph, role = house(gt[0], role_start=1)
    elif args.dataset == 'syn2':
        gt = get_ground_truth_syn1(node)  # correct
    elif args.dataset == 'syn3':
        gt = get_ground_truth_syn3(node)  # correct
        graph, role = grid(gt[0], dim=3, role_start=1)
    elif args.dataset == 'syn4':
        gt = get_ground_truth_syn4(node)  # correct
        graph, role = cycle(gt[0], 6, role_start=1)
    elif args.dataset == 'syn5':
        gt = get_ground_truth_syn5(node)  # correct
        graph, role = grid(gt[0], dim=3, role_start=1)
    elif args.dataset == 'syn6':
        gt = get_ground_truth_syn1(node)  # correct
        graph, role = bottle(gt[0], role_start=1)

    true_node_mask = np.zeros(data.edge_index.shape[1])
    true_node_mask[gt] = 1
    true_edge_mask = node_attr_to_edge(data.edge_index, true_node_mask)

    return graph, role, true_edge_mask


def get_ground_truth_syn1(node):
    base = [0, 1, 2, 3, 4]
    ground_truth = []
    offset = node % 5
    ground_truth = [node - offset + val for val in base]
    return ground_truth


def get_ground_truth_syn3(node):
    base = [0, 1, 2, 3, 4, 5, 6, 7, 8]
    buff = node - 3
    ground_truth = []
    offset = buff % 9
    ground_truth = [buff - offset + val + 3 for val in base]
    return ground_truth


def get_ground_truth_syn4(node):
    buff = node - 1
    base = [0, 1, 2, 3, 4, 5]
    ground_truth = []
    offset = buff % 6
    ground_truth = [buff - offset + val + 1 for val in base]
    return ground_truth


def get_ground_truth_syn5(node):
    base = [0, 1, 2, 3, 4, 5, 6, 7, 8]
    buff = node - 7
    ground_truth = []
    offset = buff % 9
    ground_truth = [buff - offset + val + 7 for val in base]
    return ground_truth


"""# Get explanations
prog_args = configs.arg_parse()
savename = utils.gen_filesave(prog_args)
explanations = np.load(savename, allow_pickle='TRUE').item()
"""
#evaluate_syn_explanation(explanations, prog_args)

























