# 论文（LaTeX）

## 文件
- `main.tex` —— 完整论文源码（摘要/引言/相关工作/方法框架/实验/讨论/结论/参考文献）。
- `main.pdf` —— 已用 tectonic 实际编译产出（17 页，含真实应急算例 MDVRPTW-P 求解小节、路线图与路线表；全文无手动加粗）。
- `references.bib` —— BibTeX 参考文献（与 main.tex 内嵌 thebibliography 内容一致，二选一使用）。

## 图表（参考 Wan et al. 2025 医疗资源分配论文的彩色分层框架/图示风格）
- 图1：两种求解范式对比（传统专家链路 vs 本文自然语言链路，彩色对照）。
- 图2：OptAgent 分层框架图（用户层/大模型层/执行层三泳道，模块彩色编码，含多轮纠正与执行反馈回路）。
- 算法1：OptAgent 端到端求解流程伪代码（algorithm2e）。
- 图3：MDVRPTW-P 真实应急算例的补给舰访问路线图（由求解产物 \texttt{result.json} 直接生成的 TikZ 图，$R=268.82$，与文献精确解 268.8 一致）。
- 图4：结构化提示“三段式产出”讲解图（MODEL/CODE/EXPLANATION → result.json）。
- 图5：0/1 背包完整实例（真实三段式产出）。
- 图6：各系统可运行率与最优命中率分组柱状图（pgfplots）。
- 图7：解释清晰度横向条形图 + 消融对比分组柱状图（双子图）。
- 图8：难度分层最优命中率柱状图 + 三强系统能力雷达图（polaraxis）。
- 表1：代表性工作横向对比（能力矩阵，含勾/叉/圈标记）。
- 表2/3/4：案例集、总体表现、逐案例判定。

## 依赖宏包
`ctex`（中文，需 XeLaTeX）、`amsmath`、`booktabs`、`graphicx`、`subcaption`、`tikz`、`pgfplots`（含 polar 库）、`algorithm2e`、`pifont`、`tcolorbox`、`listings`、`hyperref`、`geometry`。

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
