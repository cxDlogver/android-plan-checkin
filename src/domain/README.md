# 纯领域规则

`date.ts`提供固定IANA时区日历运算；`commands.ts`实现11个命令、幂等摘要、生命周期对账；`rules.ts`派生资格、日历集合、统计和连续。领域不依赖SQLite、React Native或系统默认时区。既有26项领域测试结果保存在验收runs目录；新查询投影位于 `src/application/projections.ts`。
