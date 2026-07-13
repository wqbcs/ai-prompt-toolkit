---
version: 3.0.0
author: AI提示词体系
updated_at: '2026-07-13'
tags:
- harmonyos
- cross-device
- distributed
- super-device
applicable_models:
- gpt-4o
- claude-3.5-sonnet
- qwen-max
- pangu-large
inheritance:
  enabled: false
locale: zh-CN
i18n_status: untranslated
market_status: draft
lint_score: 65.0
lint_last_checked: '2026-07-13T08:22:30Z'
template_type: prompt
---
# 鸿蒙跨设备分布式开发场景模板

## 概述

鸿蒙分布式能力是区别于其他操作系统的核心竞争力，包括分布式软总线、分布式数据管理、分布式任务调度等。本模板覆盖跨设备协同开发的关键场景，帮助开发者正确使用分布式API并规避常见陷阱。

---

## 一、常见陷阱（5项）

### 陷阱1：分布式数据同步冲突未处理

- `distributedKVStore`多设备同时写入同一key，后写入覆盖先写入导致数据丢失
- 未设置合适的冲突解决策略（如自动合并/自定义合并），默认策略不满足业务需求
- 网络分区时各设备数据不一致，分区恢复后同步冲突无法自动解决
- **规避**：使用`deviceColldata`级别的数据同步而非整库同步；实现自定义`ConflictResolution`策略；关键数据使用版本号/时间戳辅助冲突检测

### 陷阱2：分布式任务调度权限缺失

- 跨设备调用FA/Ability时未声明`ohos.permission.DISTRIBUTED_DATASYNC`权限，调用静默失败
- 目标设备未开启分布式权限开关，`ContinuationManager`注册失败但错误码不直观
- 使用`distributedMissionManager`跨设备迁移时未在`config.json`中配置`distributedNotificationEnabled`
- **规避**：在`module.json5`中声明所有分布式权限；运行时动态申请权限并处理拒绝场景；提供权限引导UI而非静默失败

### 陷阱3：设备发现与连接不稳定

- `DeviceManager`发现设备列表回调延迟，用户看到空列表以为没有设备
- Wi-Fi/蓝牙切换时设备连接断开，应用未监听连接状态变化导致操作失败
- 设备休眠后连接中断，唤醒后需要重新认证但应用未处理重连逻辑
- **规避**：设备发现提供加载态+超时重试；监听`deviceStateChange`事件处理连接断开；实现自动重连+指数退避机制

### 陷阱4：分布式文件访问性能问题

- 通过`distributedFileStore`访问远端文件未使用缓存，频繁IO导致卡顿
- 大文件同步传输阻塞UI线程，无进度反馈用户以为卡死
- 文件同步方向未区分上传/下载，双向同步导致冲突
- **规避**：使用本地缓存+后台同步策略；大文件分片传输+进度回调；区分`syncMode=PUSH_ONLY`/`PULL_ONLY`/`PUSH_PULL`

### 陷阱5：流转(Continuation)状态丢失

- Ability流转到目标设备后恢复的参数丢失，页面状态不完整
- 流转过程中用户操作导致状态不一致，目标设备显示旧数据
- 流转失败回退时原设备状态已被清理，出现空白页面
- **规避**：在`onContinue`中完整序列化所有状态；流转期间锁定用户操作；`onRestoreData`中严格校验数据完整性；流转失败时恢复原设备状态

---

## 二、提示词模板

{{#if industry == iot}}
### IoT行业定制版

你是鸿蒙分布式开发专家，专注于IoT设备协同场景。请帮我开发以下跨设备功能：

**需求**：[描述分布式功能需求]

**IoT特性要求**：
1. 低功耗设备适配：使用轻量级同步协议，避免频繁唤醒
2. 设备能力差异处理：大屏/小屏/无屏设备不同交互模式
3. 离线容错：网络断开时本地可用，恢复后自动同步
4. 安全合规：设备认证+数据加密传输

{{else}}
### 通用版

你是鸿蒙分布式开发专家。请帮我开发以下跨设备功能：

**需求**：[描述分布式功能需求]

**开发要求**：
1. 使用分布式数据管理实现跨设备同步
2. 处理设备发现、连接、断开全生命周期
3. 实现冲突解决策略
4. 提供流转(Continuation)状态保存与恢复

{{/if}}

---

## 三、代码示例

```typescript
import distributedKVStore from '@ohos.data.distributedKVStore';
import deviceManager from '@ohos.distributedDeviceManager';

class DistributedDataSync {
  private kvStore: distributedKVStore.SingleKVStore | null = null
  private deviceMgr: deviceManager.DeviceManager | null = null

  async init(storeId: string) {
    const kvManager = distributedKVStore.createKVManager({
      bundleName: getContext().bundleName,
    })

    this.kvStore = await kvManager.getKVStore(storeId, {
      createIfMissing: true,
      securityLevel: distributedKVStore.SecurityLevel.S1,
      autoSync: true,
    })

    this.kvStore.on('dataChange', distributedKVStore.SubscribeType.SUBSCRIBE_TYPE_ALL,
      (data) => {
        console.info(`Data changed: ${JSON.stringify(data)}`)
      }
    )
  }

  async putData(key: string, value: string) {
    if (!this.kvStore) return
    await this.kvStore.put(key, value)
  }

  async getData(key: string): Promise<string> {
    if (!this.kvStore) return ''
    return await this.kvStore.get(key)
  }
}
```

---

## 四、测试要点

1. 数据同步：双设备写入→冲突解决→最终一致性
2. 设备发现：3秒内发现同网段设备
3. 流转完整性：跨设备迁移后页面状态100%恢复
4. 离线容错：断网操作→恢复同步→数据不丢失
5. 性能指标：数据同步延迟<200ms，流转启动<1s
