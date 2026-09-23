# PKUAutoVenues-2026

通过 Web UI 或命令行创建北京大学场馆预约任务。`web_app.py` 提供网页操作和任务状态，`main.py` 执行实际预约。

## Web UI 使用

### 安装与配置

安装 [uv](https://docs.astral.sh/uv/)，并下载项目：

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
git clone https://github.com/zyy3077/PKUAutoVenues-2026
cd PKUAutoVenues-2026
```

Web UI 使用 tmux 运行后台预约任务。Ubuntu / Debian 可执行：

```bash
sudo apt install tmux
```

首次运行时复制配置文件，已有 `config.ini` 时直接编辑，避免覆盖：

```bash
cp config.sample.ini config.ini
vim config.ini
```

填写 `[iaaa]` 登录信息及验证码识别配置。通知可选，详见后文的[验证码识别](#验证码识别)和[消息通知](#消息通知)。

### 启动网页

在项目目录运行：

```bash
uv run web_app.py
```

打开 <http://127.0.0.1:8000>。如果端口被占用，可改用：

```bash
PORT=8001 uv run web_app.py
```

此时访问 <http://127.0.0.1:8001>。服务只监听本机；在远程服务器运行时，可在自己的电脑上通过 SSH 转发端口后访问：

```bash
ssh -L 8000:127.0.0.1:8000 用户名@服务器地址
```

修改网页代码后，需要重启 Web 服务并刷新页面。

### 创建预约任务

1. 选择场馆和预约日期。
2. 设置目标时段：默认一条，选择整点开始时间及连续 1 或 2 小时；点击“添加目标时间”增加备选项。程序按列表顺序尝试，成功预约后退出，并非预约所有备选项。
3. 选择二体时，在优先场地上方选择预约类型（未指定时默认半场，也可选择半场或整场）。其他场馆不显示此选项。
4. 勾选优先场地，按勾选顺序尝试；不选则随机选场。优先场地均不可用时，也会尝试其他可用场地。切换场馆或预约类型会清空场地选择。
5. 按需勾选“跳过自动支付”，点击“启动预约任务”。

| 场馆 | 可选优先场地 |
| --- | --- |
| 邱德拔羽毛球馆 | 1–12 号场 |
| 五四羽毛球馆 | 1–9 号场 |
| 邱德拔篮球馆 | 南1、北1、南2、北2 |
| 五四篮球场 | 南1、北1至南8、北8 |
| 二体篮球场（整场） | 1–4 号场，提交对应的 `北N,南N` |
| 二体篮球场（半场） | 南1、北1至南4、北4 |
| 二体篮球场（未指定，默认半场） | 南1、北1至南4、北4 |

### 查看结果与中止任务

页面显示最近 300 行日志，日志上方的结果卡片显示运行状态。任务完成后，成功结果包含日期、时段、场地和付款信息；失败结果显示原因。预约成功但自动付款失败时，会提示手动支付。

每个任务在独立 tmux 会话中运行。状态栏显示 `pku-任务ID`，旁边的复制图标可以复制会话名。点击“中止任务”会关闭对应会话；中止程序不会撤销已经提交的订单。

关闭网页或退出 Web 服务后，已启动的 tmux 任务仍会继续。当前任务索引保存在 Web 服务内存中，重启服务后不会恢复原任务管理界面；刷新页面也不会自动重新关联原任务。可使用复制的会话名查询或停止：

```bash
tmux list-sessions
tmux kill-session -t pku-任务ID
```

Web 任务输出保存在 `logs/web-tasks/任务ID.log`，退出码保存在同目录的 `.exit` 文件；任务正常退出后，对应 tmux 会话自动结束。

```bash
tail -f logs/web-tasks/任务ID.log
```

## 命令行使用

完成上述安装与 `config.ini` 配置后，也可以直接运行 `main.py`，无需启动网页。查看全部参数：

```bash
uv run main.py --help
```

### 参数说明

| 参数 | 说明 |
| --- | --- |
| `--venue` / `-v` | 场馆 ID 或支持的别名，见下表 |
| `--date` / `-d` | 日期 `YYYY-MM-DD`，或 `1`–`7` 表示目标星期一至星期日 |
| `--times` / `-t` | 按优先级排列的开始时间；`19:00/2` 表示连续两个时段，`19:00` 表示一个时段 |
| `--spaces` / `-s` | 可选，按优先级排列的场地；二体未指定类型时数字 `1` 依次匹配 `北1`、`南1`，其他场馆未指定类型时转为 `1号` |
| `--court-type` | `auto`（默认，二体按半场处理）、`half` / `半场`、`full` / `整场` |
| `--skip-pay` | 跳过自动支付，需要在订单有效期内手动付款 |

| 场馆 | ID | 别名示例 |
| --- | --- | --- |
| 邱德拔羽毛球馆 | `60` | `邱德拔羽毛球`、`qdb羽毛球` |
| 五四羽毛球馆 | `86` | `五四羽毛球`、`54羽毛球`、`ws羽毛球` |
| 邱德拔篮球馆 | `68` | `邱德拔篮球`、`qdb篮球` |
| 五四篮球场 | `82` | `五四篮球`、`54篮球` |
| 二体篮球场 | `108` | `二体` |

半场类型下，数字场地 `1` 优先匹配 `北1`，再匹配 `南1`。整场建议直接填写组合名称，如 `北1,南1`。连续时段数量最终以场馆接口的时段划分为准。

### 使用示例

以下日期为示例，运行时请替换为实际预约日期。

二体整场连续两个时段，优先选择 1 号或 2 号整场：

```bash
uv run main.py \
  --venue 二体 \
  --court-type full \
  --date 2026-09-25 \
  --times 17:00/2 \
  --spaces 北1,南1 北2,南2
```

五四羽毛球，优先尝试 15:00，再尝试 20:00：

```bash
uv run main.py \
  --venue 五四羽毛球 \
  --date 2026-09-25 \
  --times 15:00 20:00 \
  --spaces 4 5
```

五四篮球，从 19:00 开始连续两个时段：

```bash
uv run main.py \
  --venue 五四篮球 \
  --date 2026-09-25 \
  --times 19:00/2 \
  --spaces 北5 南5
```

### 预约流程

程序根据目标日期自动计算放号时间并等待。当前代码对五四篮球（`82`）和二体（`108`）使用提前一天中午 12 点，其他场馆使用提前三天中午 12 点；实际执行时间会打印在日志中。

程序在放号前登录，随后识别验证码、查询场地、提交订单，并根据设置支付和发送通知。日志保存在 `logs/`。请保持运行机器开机、联网。

### 后台与定时运行

### 使用 tmux 挂起任务

`main.py` 会根据 `--date` 自动计算放号时间并等待，因此可以提前在 `tmux` 中启动。下面的示例预约 2026 年 9 月 24 日二体整场 20:00-22:00，优先选择 `北3,南3`，其次选择 `北4,南4`：

```bash
cd ~/PKUAutoVenues-2026
tmux new -s pku-er

uv run main.py \
  --venue 二体 \
  --court-type full \
  --date 2026-09-24 \
  --times 20:00/2 \
  --spaces '北3,南3' '北4,南4'
```

启动后按 `Ctrl-B`，再按 `D` 分离会话，程序会继续在后台运行。重新查看或停止任务：

```bash
tmux attach -t pku-er       # 重新进入会话
tmux list-sessions          # 查看 tmux 会话
tmux kill-session -t pku-er # 停止会话及其中的程序
```

日志保存在 `logs/` 目录中，也可以用下面的命令实时查看最新日志：

```bash
tail -f logs/*.log
```

请确保机器在放号时间前保持开机和联网，并且不要重复启动多个预约进程。

如果想要定时运行（一次），可以使用 Linux 的 `at` 命令：

```bash
sudo apt install at

sudo systemctl start atd
sudo systemctl enable atd
```

```bash
echo 'cd ~/PKUAutoVenues-2026 && \
      uv run main.py \
        --venue 五四羽毛球 \
        --date 2026-05-03 \
        --times 19:00/2 19:00 \
        --spaces 9 8' \
| at 11:50 2026-04-30
```

- 记得把 `~/PKUAutoVenues-2026` 替换成项目的实际位置！

- `atq` 查看所有已设置的定时任务，`atrm 任务号` 取消任务

如果想要周期性地定时运行（如固定每周四中午预约周日的场地），可以使用 Linux 的 `cron` 服务：

```bash
(crontab -l 2>/dev/null; \
 echo "50 11 * * 4 \
       cd ~/PKUAutoVenues-2026 && \
       $(which uv) run main.py \
         -v 邱德拔羽毛球 \
         -d 7 \
         -t 19:00 20:00") \
| crontab -
```

- 这里 `50 11 * * 4` 表示每周四 11:50，`-d 7` 指定要预约周日的场地

- 记得把 `~/PKUAutoVenues-2026` 替换成项目的实际位置！

- `crontab -l` 查看所有已设置的周期任务，`crontab -e` 打开编辑器管理所有周期任务（上面这串命令和 `crontab -e` 手动追加一行的效果是一样的）


## 验证码识别

本项目推荐使用 [TT 识图](http://www.ttshitu.com/) 进行验证码识别，识别一次价格为 0.016 元，充值 1 元大约可以识别 62 次。你需要在网站上注册账号（如果已有账号且很久没用的话需要在网站上解锁账号），并在 `config.ini` 的 `[recognize:ttshitu]` 部分填写账号的用户名和密码。

（如果你已经在超级鹰里充了很多钱，）你也可以选择使用 [超级鹰](https://www.chaojiying.com/) 平台进行验证码识别，识别一次价格为 0.028 元，一次至少充 19 元（看起来比 [去年](https://github.com/qqworld-tutu/PKUautoBookingVenues-fixed-by-cq-tutu#api) 更坑了）。你需要在 `config.ini` 的 `[recognize]` 部分将 `method` 的值改为 `chaojiying`，并在 `[recognize:chaojiying]` 部分填写账号的用户名、密码、软件 ID。

非高峰时段，TT 识图的响应耗时约为 0.5 秒，超级鹰约为 0.4 秒；高峰时段（12:00 前后），TT 识图的响应耗时约为 1~1.5 秒，超级鹰尚未充分测试。

## 消息通知

可以选择以下通知方式中的一种，在预约流程完成后会自动向你发送结果。你需要在 `config.ini` 中修改 `[notify]` 部分 `method` 的值，并在对应的 `[notify:{method}]` 部分填写该通知方式所需的配置。（你也可以保留 `method = none`，表示不启用通知功能，这样下方配置都无需修改，可以直接跳到 [Web UI 使用](#web-ui-使用) 部分。）

### 1. Email：给自己发邮件

基于 SMTP 协议，用自己的邮箱账号给自己发送邮件，手机上的邮箱客户端（如网易邮箱大师等）就可以很方便地收到通知。目前仅适配了 `@stu.pku.edu.cn`、`@pku.edu.cn`、`@qq.com`、`@163.com`、`@126.com` 邮箱。

以 `@stu.pku.edu.cn` 邮箱为例（其他邮箱类似），你需要在浏览器中登录 [网页版邮箱](https://mail.stu.pku.edu.cn/)，进入 “设置” - **“客户端设置”** 页面，点击 **“生成客户端授权密码”**，自行设置合适的客户端名称（如 “PKUAutoVenues”）和到期时间，将邮箱地址和 **生成的授权码**（而不是原始密码）填到 `config.ini` 的 `[notify:email]` 部分。注意，为了通过 Python 发送邮件，需要 **允许非官方客户端使用 SMTP 服务**，即页面中 “非网易官方客户端” 的权限至少要有 “IMAP / SMTP 协议” 和 “POP / SMTP 协议” 其中一项。

> 下面三种方式都类似于 “向注册了特定 SendKey 的客户端发通知”，小标题说明了 “客户端” 的存在形式：

### 2. Server酱<sup>3</sup>：手机 APP（主流手机系统均可安装）

1. 打开 [Server酱<sup>3</sup> 官网](https://sc3.ft07.com/)，使用微信扫码登录，在 [SendKey 页面](https://sc3.ft07.com/sendkey) 复制 SendKey（以 `sctp` 开头的字符串），填到 `config.ini` 的 `[notify:sc3]` 部分
2. 访问 [下载页面](https://sc3.ft07.com/client)，在手机上安装 Server酱 APP，启动 APP 后填入 SendKey 或扫描 [SendKey 页面](https://sc3.ft07.com/sendkey) 上的二维码以登录

### 3. Server酱<sup>Turbo</sup>：微信服务号

打开 [Server酱<sup>Turbo</sup> 官网](https://sct.ftqq.com/)，使用微信扫码登录（关注方糖服务号），在 [Key&API 页面](https://sct.ftqq.com/sendkey) 复制 SendKey（以 `SCT` 开头的字符串），填到 `config.ini` 的 `[notify:sct]` 部分

### 4. Bark：手机 APP（仅 iOS）

在手机 App Store 下载 [Bark](https://apps.apple.com/cn/app/id1403753865)，打开 APP 首页并复制任意一个测试 URL，`https://api.day.app/` 后面的一串字符串就是你的推送 Key，将它填到 `config.ini` 的 `[notify:bark]` 部分


## 预览

<img src="assets/preview.png" alt="Preview">

<img src="assets/notification.png" alt="Notification" width="500">

## 致谢

- codebase from [goudanZ1/PKUAutoVenues-2026](https://github.com/goudanZ1/PKUAutoVenues-2026)
