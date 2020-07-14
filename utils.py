import yaml


def set_matlotlib(plt):

    plt.rcParams['grid.color'] = 'lightgrey'
    plt.rcParams['grid.linestyle'] = 'solid'
    plt.rcParams['grid.linewidth'] = 0.5


def parse_yaml(filename):
    with open(filename, "r") as stream:
        config = yaml.safe_load(stream)
    return config
