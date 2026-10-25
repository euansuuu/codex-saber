---
name: saber-setup
description: 安装、检查或排查本机 Saber 原生宠物及插件技能；适用于 Saber 显示、角色切换、素材格式和本地设置问题。
---

在用户现有 Codex 桌面环境中配置本插件附带的 Saber 角色。

角色包位于本技能目录的 ../../pets/saber-knight/，安装脚本为 ../../scripts/install-pet.ps1。先读取 pet.json 并确认 spritesheet.png 存在；当前素材为 v1，1536 × 1872，8 列 9 行。

用户要求本地安装或修复时，运行脚本将素材放入当前 CODEX_HOME（未设置时为用户目录下 .codex）的 pets/saber-knight。脚本校验文件、跳过相同内容并保护已存在的不同内容。安装成功后，指导用户在 Settings → Pets 中 Refresh、选择 Saber，并用 /pet 显示。以命令执行结果报告安装，角色已被选中或已显示需另有实际证据。

用户已要求升级或替换旧版时，可给脚本传入 -Upgrade；它会先将旧角色文件备份到 CODEX_HOME/pets-backups/saber-knight/，再替换。仅询问设置不执行升级。升级后要 Refresh 并重新选择 Saber，避免宿主继续缓存旧图。

新版桌面端可能已把 custom:saber-knight 迁移到 ChatGPT Pets 云端条目。安装脚本会检查 .codex-global-state.json 中的 migrated-cloud-pet-ids-v1 并提示；不修改该状态文件。此时本地复制成功和 Refresh 都不能证明已更新云端素材。

用户已要求修复、升级或同步当前 Saber 时，使用 Pets 插件核对 list_pets 的 active_pet_id 与迁移记录，确认该条目为用户自定义 Saber。按 Pets 更新流程读取现有素材并备份，验证要同步的本插件 spritesheet.png；用户已看过该版动画时可同步这份已批准素材，不凭空扩展动作或升级布局。调用 validate_pet_spritesheet，通过后 prepare_pet_upload，再 update_pet 到同一个稳定 ID。保持名称、描述及原有选中状态，不创建重复角色，不直接改账号状态或访问令牌。最后 list_pets 复核身份与选中状态，下载云端文件并比较解码后的 RGBA 像素；编码后的文件哈希可能因服务重编码而不同。缺少 Pets 工具时报告未完成云端同步，不能只让用户再次 Refresh。

当前包含召唤问候、喝茶待机、挥剑执行、光屏检索、举剑庆祝、异常求助六类关键帧表演。检索姿态用于 running 的后半段与 waiting，并不检测实际搜索工具调用。鼠标悬停原生角色时，宿主优先播放 jumping；排查只跳跃时先移开鼠标，再观察任务状态。review 是任务完成待阅读，非代码检查过程。

思考和工具执行在当前宿主中共享 running，没有独立的 thinking 状态。当前版本会在约 2.46 秒后让 running 动画返回 idle，即使任务仍在运行；普通插件及 animation.json 不能改变宿主的播放时长。区分素材没更新、动作未触发和触发后自动待机，不通过重复生成素材冒充修复宿主状态调度。

如果入口不可用，报告当前客户端版本和已安装路径，并核对宿主支持情况；普通技能不能创建宿主未提供的角色展示层。对已有角色文件与插件缓存先检查再处理，保留用户修改。

用户只询问设置时先解释，不执行安装。角色动画由宿主状态调度；本技能不替换主界面或改动权限设置。对话风格通过 saber 技能启用。本地开发不连接或发布到 GitHub。
