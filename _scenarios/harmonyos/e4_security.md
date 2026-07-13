---
version: 3.0.0
author: AI提示词体系
updated_at: '2026-07-13'
tags:
- harmonyos
- security
- access-control
- encryption
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
lint_score: 60.0
lint_last_checked: '2026-07-13T06:57:46Z'
template_type: prompt
---
# 鸿蒙安全与权限管理场景模板

## 概述

鸿蒙安全体系基于TEE（可信执行环境）+ ACE（访问控制引擎）+ HUKS（通用密钥管理）构建多层防护。本模板覆盖鸿蒙应用安全开发的核心场景，包括权限管理、数据加密、安全存储、应用沙箱等，帮助开发者构建安全合规的鸿蒙应用。

---

## 一、常见陷阱（5项）

### 陷阱1：权限申请时机不当

- 在`onCreate`中一次性申请所有权限，用户被大量弹窗吓到直接拒绝
- `ohos.permission.LOCATION`等用户授权权限未提供"拒绝后引导"逻辑，用户拒绝后功能不可用且无提示
- 使用`ohos.permission.APPROXIMATELY_LOCATION`时未同时申请精确位置权限，定位精度不满足业务需求
- **规避**：按需申请权限（用户触发功能时再申请）；实现权限拒绝后的说明UI+二次申请引导；粗略定位+精确定位组合申请

### 陷阱2：敏感数据明文存储

- 用户Token/密码直接存储在`Preferences`中，root设备可直接读取
- 数据库未加密，`relationalStore`文件可被提取分析
- 日志中输出敏感信息（手机号、身份证），调试日志泄漏到生产环境
- **规避**：敏感数据使用`@ohos.security.huks`加密后存储；数据库使用`encrypted: true`选项；生产环境关闭DEBUG日志；使用`@ohos.security.cryptoFramework`进行加解密

### 陷阱3：HUKS密钥管理不当

- 密钥别名使用硬编码字符串，不同应用可能冲突
- 使用`HUKS_TAG_PURPOSE`未同时设置加密和解密用途，运行时报错
- 密钥未设置有效期（`HUKS_TAG_ACTIVE_DATETIME`），长期使用同一密钥增加泄露风险
- **规避**：密钥别名使用`bundleName + 业务标识`确保唯一；完整声明密钥用途和参数；设置合理的密钥有效期和轮转策略

### 陷阱4：应用沙箱越界访问

- 使用`@ohos.file.fs`访问沙箱外路径，API直接抛异常但未捕获导致崩溃
- 通过`@ohos.file.picker`选择文件后直接使用原始路径而非URI，沙箱限制无法访问
- 临时文件未清理导致沙箱存储持续增长
- **规避**：文件访问始终使用沙箱内路径或URI方式；`picker`返回结果使用`uri`而非`filePath`；定期清理缓存目录

### 陷阱5：网络安全配置缺失

- 未配置`network-security-config`，HTTP明文请求在Android 9+/HarmonyOS上默认被阻止
- 证书校验不严格，中间人攻击风险
- WebView加载HTTP页面被安全策略阻止
- **规避**：配置`domain-config`声明允许的域名和证书策略；生产环境强制HTTPS；WebView使用`onSslErrorReceive`回调严格校验证书

---

## 二、提示词模板

{{#if industry == finance}}
### 金融行业定制版

你是鸿蒙安全开发专家，专注于金融级应用安全。请帮我实现以下安全功能：

**需求**：[描述安全功能需求]

**金融合规要求**：
1. 数据加密：所有敏感数据使用HUKS硬件级加密
2. 通信安全：双向TLS认证+证书钉扎(Certificate Pinning)
3. 身份认证：集成生物识别(FaceID/Fingerprint)
4. 审计日志：关键操作可追溯
5. 防篡改：应用签名校验+运行时完整性检测

{{else}}
### 通用版

你是鸿蒙安全开发专家。请帮我实现以下安全功能：

**需求**：[描述安全功能需求]

**安全要求**：
1. 权限按需申请+拒绝引导
2. 敏感数据加密存储
3. 密钥安全管理
4. 网络通信安全

{{/if}}

---

## 三、代码示例

```typescript
import huks from '@ohos.security.huks';
import cryptoFramework from '@ohos.security.cryptoFramework';

class SecureDataStore {
  private keyAlias: string = `${getContext().bundleName}_secure_key`

  async initKey() {
    const properties: huks.HuksOptions = {
      properties: [
        { tag: huks.HuksTag.HUKS_TAG_ALGORITHM, value: huks.HuksKeyAlg.HUKS_ALG_AES },
        { tag: huks.HuksTag.HUKS_TAG_KEY_SIZE, value: huks.HuksKeySize.HUKS_AES_KEY_SIZE_256 },
        { tag: huks.HuksTag.HUKS_TAG_PURPOSE, value: huks.HuksKeyPurpose.HUKS_KEY_PURPOSE_ENCRYPT |
          huks.HuksKeyPurpose.HUKS_KEY_PURPOSE_DECRYPT },
        { tag: huks.HuksTag.HUKS_TAG_PADDING, value: huks.HuksKeyPadding.HUKS_PADDING_PKCS7 },
        { tag: huks.HuksTag.HUKS_TAG_BLOCK_MODE, value: huks.CipherMode.HUKS_MODE_CBC },
      ],
    }

    const isExist = await huks.isKeyItemExist(this.keyAlias, properties)
    if (!isExist) {
      await huks.generateKeyItem(this.keyAlias, properties)
    }
  }

  async encrypt(plainText: string): Promise<string> {
    const options: huks.HuksOptions = {
      properties: [
        { tag: huks.HuksTag.HUKS_TAG_ALGORITHM, value: huks.HuksKeyAlg.HUKS_ALG_AES },
        { tag: huks.HuksTag.HUKS_TAG_PURPOSE, value: huks.HuksKeyPurpose.HUKS_KEY_PURPOSE_ENCRYPT },
        { tag: huks.HuksTag.HUKS_TAG_PADDING, value: huks.HuksKeyPadding.HUKS_PADDING_PKCS7 },
        { tag: huks.HuksTag.HUKS_TAG_BLOCK_MODE, value: huks.CipherMode.HUKS_MODE_CBC },
      ],
      inData: new Uint8Array(Array.from(plainText).map(c => c.charCodeAt(0))),
    }

    const result = await huks.initSession(this.keyAlias, options)
    const finishResult = await huks.finishSession(result.handle, options)
    return btoa(String.fromCharCode(...finishResult.outData))
  }
}
```

---

## 四、测试要点

1. 权限流程：正常授权→拒绝→引导→二次授权全链路
2. 加密完整性：加密→解密后数据一致性100%
3. 密钥安全：密钥不可导出（HUKS安全世界）
4. 沙箱隔离：沙箱外文件访问100%被拦截
5. 性能影响：加密/解密单次<10ms（AES-256-CBC）
