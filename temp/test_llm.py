"""测试 LLM 调用是否正常 (诊断 docbot 报告生成失败)."""
import asyncio
import os
import sys

sys.path.insert(0, "/app")


async def test_llm():
    import litellm
    from src.config.settings import get_settings

    s = get_settings()
    print(f"STRATEGIC_LLM: {s.strategic_llm}")
    print(f"SMART_LLM: {s.smart_llm}")
    print(f"FAST_LLM: {s.fast_llm}")
    print(f"DEEPSEEK_API_KEY: {os.environ.get('DEEPSEEK_API_KEY', '')[:10]}...")
    print(f"ZHIPU_API_KEY: {os.environ.get('ZHIPU_API_KEY', '')[:10]}...")
    print(f"llm_timeout: {s.llm_timeout}")

    # 测试 STRATEGIC (deepseek-v4-pro)
    try:
        r = await litellm.acompletion(
            model="deepseek/deepseek-v4-pro",
            messages=[{"role": "user", "content": "回复 OK"}],
            api_key=os.environ["DEEPSEEK_API_KEY"],
            timeout=30,
            max_tokens=10,
        )
        print(f"[OK] STRATEGIC: {r.choices[0].message.content[:50]}")
    except Exception as e:
        print(f"[FAIL] STRATEGIC: {type(e).__name__}: {str(e)[:300]}")

    # 测试 SMART (deepseek-v4-flash)
    try:
        r = await litellm.acompletion(
            model="deepseek/deepseek-v4-flash",
            messages=[{"role": "user", "content": "回复 OK"}],
            api_key=os.environ["DEEPSEEK_API_KEY"],
            timeout=30,
            max_tokens=10,
        )
        print(f"[OK] SMART: {r.choices[0].message.content[:50]}")
    except Exception as e:
        print(f"[FAIL] SMART: {type(e).__name__}: {str(e)[:300]}")

    # 测试 FAST (glm-4-flash)
    try:
        r = await litellm.acompletion(
            model="zhipuai/glm-4-flash",
            messages=[{"role": "user", "content": "回复 OK"}],
            api_key=os.environ["ZHIPU_API_KEY"],
            timeout=30,
            max_tokens=10,
        )
        print(f"[OK] FAST: {r.choices[0].message.content[:50]}")
    except Exception as e:
        print(f"[FAIL] FAST: {type(e).__name__}: {str(e)[:300]}")


if __name__ == "__main__":
    asyncio.run(test_llm())
