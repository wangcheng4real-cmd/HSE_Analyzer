import matplotlib

def init_matplotlib_font():
    matplotlib.rcParams["font.family"] = "sans-serif"
    matplotlib.rcParams["font.sans-serif"] = [
        "Microsoft YaHei",   # 微软雅黑（Windows最稳）
        "SimHei",            # 黑体
        "Arial Unicode MS"
    ]

    matplotlib.rcParams["axes.unicode_minus"] = False

