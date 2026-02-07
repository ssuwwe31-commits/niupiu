#!/bin/bash

echo "=========================================="
echo "测试质量评估 API 端点"
echo "=========================================="

BASE_URL="http://localhost:8001/api"

echo ""
echo "测试 1: 单剧本质量评估"
echo "=========================================="
curl -X POST "$BASE_URL/quality-evaluate" \
  -H "Content-Type: application/json" \
  -d '{
    "script_content": "【场景】李明的办公室\n\n李明：王总，这个项目我已经尽力了，但是客户那边的要求一直在变。\n王总：李明，我不管客户怎么变，你必须要按时交付。这是你的责任。\n李明：可是这样下去质量很难保证啊。\n王总：质量是其次，按时才是关键。你明白吗？\n李明：……我明白了。",
    "plot_context": "项目经理李明面临客户需求频繁变更和上级王总的严格要求",
    "characters": ["李明", "王总"]
  }'

echo ""
echo ""
echo "测试 2: 自定义权重评估"
echo "=========================================="
curl -X POST "$BASE_URL/quality-evaluate" \
  -H "Content-Type: application/json" \
  -d '{
    "script_content": "【场景】咖啡厅\n\n张伟：小芳，我有件事想跟你说。\n小芳：什么事？\n张伟：我喜欢你很久了。\n小芳：……\n张伟：我知道这可能很突然，但是……\n小芳：对不起，我有喜欢的人了。\n张伟：是……是谁？\n小芳：这重要吗？",
    "plot_context": "张伟向小芳表白",
    "characters": ["张伟", "小芳"],
    "custom_weights": {
      "conflict_intensity": 0.30,
      "emotion_rendering": 0.25,
      "character_consistency": 0.15,
      "dialogue_naturalness": 0.15,
      "dramatic_tension": 0.10,
      "overall_coherence": 0.05
    }
  }'

echo ""
echo ""
echo "测试 3: 批量评估"
echo "=========================================="
curl -X POST "$BASE_URL/quality-evaluate-batch" \
  -H "Content-Type: application/json" \
  -d '{
    "scripts": [
      "【场景】客厅\n\n父亲：你到底什么时候才能长大？\n儿子：我已经长大了！\n父亲：那就别整天玩游戏！\n儿子：你不懂我！",
      "【场景】餐厅\n\n陈总：小李，今天的会议准备得怎么样？\n小李：陈总，所有资料都已经准备好了。\n陈总：很好，记得提前十分钟到场。\n小李：明白，我会提前去检查设备。"
    ],
    "plot_context": "父子冲突和职场对话",
    "characters": ["父亲", "儿子", "陈总", "小李"]
  }'

echo ""
echo ""
echo "测试 4: 剧本生成时启用质量评估"
echo "=========================================="
curl -X POST "$BASE_URL/generate-script-deepseek" \
  -H "Content-Type: application/json" \
  -d '{
    "plot_context": "职场新员工遇到困难",
    "required_conflict": "工作压力",
    "required_emotion": "焦虑",
    "characters": ["小王", "张经理"],
    "enable_quality_evaluation": true
  }'

echo ""
echo ""
echo "=========================================="
echo "测试完成"
echo "=========================================="
