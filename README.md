# Track Stargazers

![截图](https://i.imgur.com/a42BgPi.png)

这个仓库包含一个 GitHub Actions 工作流，用于跟踪和记录仓库的 Stargazers（加星用户），并将每日新增关注者发送到指定的飞书群。

## 功能特点

- 自动跟踪仓库的 Stargazers。
- 将 Stargazers 数据保存到 `stargazers.json` 文件中。
- 每日新增关注者监控，并发送到指定的飞书群。
- 自动定时执行：每天 UTC 时间 3:00（北京时间 11:00）自动运行。
- 生成每日报告：每次运行时生成新增 Stargazers（new.csv）和总 Stargazers（total.csv）的表格。

## 环境变量

在你的 GitHub 仓库中，设置以下 Secrets：

- `ACCESS_TOKEN`：你的 GitHub 个人访问令牌（需要有 `repo` 权限）。
- `TARGET_REPO`: GitHub 仓库名，格式为 `owner/repo`。
- `FEISHU_WEBHOOK`：飞书群的 Webhook URL。

你可以参考 `example.env` 文件来配置这些环境变量。

## 用途

- 自动跟踪仓库的 Stargazers。
- 将 Stargazers 数据保存到 `stargazers.json` 文件中。
- 每日新增关注者监控，并发送到指定的飞书群。

## 使用方法

1. 将 `.github/workflows/star.yml` 文件添加到你的仓库中。
2. 确保 `star.py` 脚本文件在你的仓库根目录中。
3. 进入 GitHub 仓库页面，点击 `Actions` 标签，选择 `Run Track Stars` 工作流，点击 `Run workflow` 按钮手动触发工作流。

## 文件说明

- `.github/workflows/star.yml`：GitHub Actions 工作流配置文件，定义了自动运行的时间和步骤。
- `stargazers.json`：存储 Stargazers 数据的文件，每次运行时更新。
- `star.py`：用于获取和更新 Stargazers 数据的 Python 脚本。
- `README.md`：项目说明文件。
- `.gitignore`：Git 忽略文件配置。
- `example.env`：环境变量示例文件。
- `new.csv`：每次运行时生成的新增 Stargazers 表格。
- `total.csv`：每次运行时生成的总 Stargazers 表格。

## 自动化运行

工作流程每天自动运行一次，您也可以在 GitHub 仓库的 Actions 页面手动触发运行。每次运行后，新的 Stargazers 数据和生成的 CSV 文件会作为 artifacts 上传，可以在 Actions 运行记录中下载查看。

如有问题或建议，请提交 issue 或 pull request。