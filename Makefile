.DEFAULT_GOAL := help
.PHONY: help start go status explain back check reset

help:  ## 显示这份帮助
	@echo ""
	@echo "  从一个想法，到一个能用的东西"
	@echo ""
	@echo "  第一次用："
	@echo "    ./loop.sh start \"我想做一个帮我记客户跟进的小工具\""
	@echo ""
	@echo "  之后："
	@grep -E '^[a-z-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "    make %-10s %s\n", $$1, $$2}'
	@echo ""

start: ## 开始（等价于 ./loop.sh start，需要先想好一句话）
	@echo '请直接跑：./loop.sh start "你想做什么"'

go:      ## 继续往下跑
	@./loop.sh go

status:  ## 看现在到哪一步了
	@./loop.sh status

explain: ## 用大白话讲一遍现在什么情况
	@./loop.sh explain

back:    ## 退回上一步重做
	@./loop.sh back

check:   ## 自己跑一遍检查，看东西还正常吗
	@bash scripts/check.sh

reset:   ## 全部清空重来（会先自动备份）
	@./loop.sh reset
