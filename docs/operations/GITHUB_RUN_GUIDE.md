# ROGII GitHub / 跑分入口

这是一份轻量入口文档，真正的完整流程请看：

- [`docs/operations/FULL_INFERENCE_GUIDE.md`](/Users/hwaigc/太空垃圾站/ROG%20II地质勘测/docs/operations/FULL_INFERENCE_GUIDE.md)
- [`docs/operations/part2_server_full_run_guide.md`](/Users/hwaigc/太空垃圾站/ROG%20II地质勘测/docs/operations/part2_server_full_run_guide.md)

当前口径先记住三点：

- 原始数据只认 `data/raw/`
- Part 2 旧成品已经清理，不能直接拿来当最终结果
- 最终提交链路是 `blend -> postprocess -> make_submission`

如果你要给别人交接，直接把上面两份文档发过去就够了。

