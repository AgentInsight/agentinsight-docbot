"""测试 LLM 调用完整响应 (诊断空内容问题)."""
import asyncio
import os
import sys

sys.path.insert(0, "/app")


async def test_llm_full():
    import litellm
    from importlib.metadata import version
    from src.config.settings import get_settings

    s = get_settings()
    print(f"litellm version: {version('litellm')}")
    print(f"STRATEGIC_LLM: {s.strategic_llm}")
    print(f"SMART_LLM: {s.smart_llm}")
    print(f"FAST_LLM: {s.fast_llm}")
    print(f"DEEPSEEK_API_KEY: {os.environ.get('DEEPSEEK_API_KEY', '')[:15]}...")
    print()

    # 测试 STRATEGIC (deepseek-v4-pro) - 完整响应
    print("=" * 60)
    print("Testing STRATEGIC: deepseek/deepseek-v4-pro")
    try:
        r = await litellm.acompletion(
            model="deepseek/deepseek-v4-pro",
            messages=[{"role": "user", "content": "请回复'你好，我是AI助手'"}],
            api_key=os.environ["DEEPSEEK_API_KEY"],
            timeout=60,
            max_tokens=100,
        )
        print(f"  id: {r.id}")
        print(f"  model: {r.model}")
        print(f"  content: '{r.choices[0].message.content}'")
        print(f"  finish_reason: {r.choices[0].finish_reason}")
        print(f"  usage: prompt={r.usage.prompt_tokens} completion={r.usage.completion_tokens}")
    except Exception as e:
        print(f"  FAIL: {type(e).__name__}: {str(e)[:500]}")

    print()

    # 测试 SMART (deepseek-v4-flash) - 完整响应
    print("=" * 60)
    print("Testing SMART: deepseek/deepseek-v4-flash")
    try:
        r = await litellm.acompletion(
            model="deepseek/deepseek-v4-flash",
            messages=[{"role": "user", "content": "请回复'你好，我是AI助手'"}],
            api_key=os.environ["DEEPSEEK_API_KEY"],
            timeout=60,
            max_tokens=100,
        )
        print(f"  id: {r.id}")
        print(f"  model: {r.model}")
        print(f"  content: '{r.choices[0].message.content}'")
        print(f"  finish_reason: {r.choices[0].finish_reason}")
        print(f"  usage: prompt={r.usage.prompt_tokens} completion={r.usage.completion_tokens}")
    except Exception as e:
        print(f"  FAIL: {type(e).__name__}: {str(e)[:500]}")

    print()

    # 测试 FAST (zhipuai/glm-4-flash) - 完整响应
    print("=" * 60)
    print("Testing FAST: zhipuai/glm-4-flash")
    try:
        r = await litellm.acompletion(
            model="zhipuai/glm-4-flash",
            messages=[{"role": "user", "content": "请回复'你好，我是AI助手'"}],
            api_key=os.environ["ZHIPU_API_KEY"],
            timeout=60,
            max_tokens=100,
        )
        print(f"  id: {r.id}")
        print(f"  model: {r.model}")
        print(f"  content: '{r.choices[0].message.content}'")
        print(f"  finish_reason: {r.choices[0].finish_reason}")
        print(f"  usage: prompt={r.usage.prompt_tokens} completion={r.usage.completion_tokens}")
    except Exception as e:
        print(f"  FAIL: {type(e).__name__}: {str(e)[:500]}")

    print()

    # 测试 DeepSeek 原生 API (不走 litellm)
    print("=" * 60)
    print("Testing DeepSeek native API (openai compatible)")
    try:
        import httpx
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {os.environ['DEEPSEEK_API_KEY']}"},
                json={
                    "model": "deepseek-chat",
                    "messages": [{"role": "user", "content": "请回复'你好，我是AI助手'"}],
                    "max_tokens": 100,
                },
            )
            print(f"  status: {resp.status_code}")
            data = resp.json()
            print(f"  model: {data.get('model', '')}")
            print(f"  content: '{data['choices'][0]['message']['content']}'")
            print(f"  finish_reason: {data['choices'][0].get('finish_reason')}")
            print(f"  usage: {data.get('usage', {})}")
    except Exception as e:
        print(f"  FAIL: {type(e).__name__}: {str(e)[:500]}")


if __name__ == "__main__":
    asyncio.run(test_llm_full())
