# Track Stargazers

这个仓库包含一个 GitHub Actions 工作流，用于跟踪和记录仓库的 Stargazers（加星用户），并将每日新增关注者发送到指定的飞书群。

## 环境变量

在你的 GitHub 仓库中，设置以下 Secrets：

- `ACCESS_TOKEN`：你的 GitHub 个人访问令牌（需要有 `repo` 权限）。
- `REPO_OWNER`：你的 GitHub 用户名或组织名。
- `REPO_NAME`：你的仓库名。
- `FEISHU_WEBHOOK`：飞书群的 Webhook URL。

## 用途

- 自动跟踪仓库的 Stargazers。
- 将 Stargazers 数据保存到 `stargazers.json` 文件中。
- 每日新增关注者监控，并发送到指定的飞书群。

## 使用方法

1. 将 `.github/workflows/star.yml` 文件添加到你的仓库中。
2. 确保 `star.py` 脚本文件在你的仓库根目录中。
3. 进入 GitHub 仓库页面，点击 `Actions` 标签，选择 `Run Track Stars` 工作流，点击 `Run workflow` 按钮手动触发工作流。

## 文件说明

- `.github/workflows/star.yml`：GitHub Actions 工作流配置文件。
- `stargazers.json`：存储 Stargazers 数据的文件。
- `star.py`：用于获取和更新 Stargazers 数据的 Python 脚本。
- `README.md`：项目说明文件。
- `.gitignore`：Git 忽略文件配置。
- `.env`：环境变量文件（可选）。

如有问题或建议，请提交 issue 或 pull request。