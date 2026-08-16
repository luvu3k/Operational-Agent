# 论文（LaTeX）

## 文件
- `main.tex` —— 完整论文源码（摘要/引言/相关工作/方法框架/实验/讨论/结论/参考文献）。
- `main.pdf` —— **已用 tectonic 实际编译产出**（11 页，含 5 张矢量图）。
- `references.bib` —— BibTeX 参考文献（与 main.tex 内嵌 thebibliography 内容一致，二选一使用）。

## 图表（均为源码内矢量绘制，无外部图片依赖）
- 图1：五模块端到端架构流程图（TikZ，含多轮纠正回路与执行反馈回路）。
- 图2：0/1 背包完整实例（真实三段式产出 MODEL/CODE/EXPLANATION）。
- 图3：各系统可运行率与最优命中率分组柱状图（pgfplots）。
- 图4：解释清晰度横向条形图 + 消融对比分组柱状图（pgfplots，双子图）。
- 图5：逐案例×系统判定矩阵热力图（TikZ）。

## 依赖宏包
`ctex`（中文，需 XeLaTeX）、`amsmath`、`booktabs`、`graphicx`、`subcaption`、`tikz`、`pgfplots`、`tcolorbox`、`listings`、`hyperref`、`geometry`。

## 编译方式
论文含中文，需用 **XeLaTeX** 类引擎。以下任选其一：

### 方式 A：tectonic（本仓库已验证可编译，自动下载所需宏包）
```bash
# 安装（自包含单文件，无需完整 TeX 发行版）：
curl -fsSL https://drop-sh.fullyjustified.net | sh   # 或从 GitHub releases 下载 tectonic 二进制

cd paper
tectonic main.tex        # 一步生成 main.pdf（首次运行会联网拉取字体/宏包）
```

### 方式 B：本地安装完整 TeX 后编译
```bash
# macOS：
brew install --cask mactex-no-gui      # 完整；或
brew install --cask basictex && sudo tlmgr install ctex booktabs listings pgfplots tcolorbox subcaption

cd paper
xelatex main.tex
xelatex main.tex        # 跑两遍以生成交叉引用
```
`main.tex` 已内嵌 `thebibliography`，无需 bibtex 即可出参考文献。

### 方式 C：在线编译（免安装）
把 `main.tex` 上传到 Overleaf，编译器选 **XeLaTeX** 即可直接生成 PDF。

## 数据来源
论文所有实验数字均来自 `../shiyan/`（真实运行）：
- 总体与逐案例结果：`../shiyan/results/summary.md`、`summary.csv`、`stats.json`
- 解释清晰度：`../shiyan/results/clarity_avg.json`、`clarity_scores.json`
- 汇总要点：`../shiyan/FINAL_RESULTS.md`
- 实验协议：`../shiyan/PROTOCOL.md`
