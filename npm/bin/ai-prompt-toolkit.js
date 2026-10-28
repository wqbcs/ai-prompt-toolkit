#!/usr/bin/env node
'use strict';
// ai-prompt-toolkit — npm 薄包装器入口（P1-04）。
// 最小职责（06_发布与采用 §4 裁定）：仅参数/退出码透传到 Python 包（PyPI 真源）。
// 零 npm 依赖：只用 node 内建模块。
require('../lib/runner').main();
