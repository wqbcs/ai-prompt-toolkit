"""python -m ai_prompt_toolkit 入口 (R212)"""

from __future__ import annotations

import sys

from ai_prompt_toolkit.cli_core import main

if __name__ == "__main__":
    # R226-P1-14: preflight hook 子入口 — AI 编码助手 UserPromptSubmit hook
    # (质量 preflight, 非 CI 门禁; 与门禁路径语义隔离, 见 preflight_hook.py 模块注)
    if "--preflight-hook" in sys.argv[1:]:
        from ai_prompt_toolkit.cli.preflight_hook import main as _hook_main

        sys.exit(_hook_main())
    main()
