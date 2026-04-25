据 pytest.ini 配置，这个项目使用 pytest 运行测试。以下是常用命令：                                        
                               
1. 运行所有测试                                                                                             
pytest                   
                                                                                                            
2. 运行指定测试文件                                                                                         
pytest test/internal/handler/test_api_tool_handler.py                                                       
                                                                                                            
3. 运行指定测试类                                                                                           
pytest test/internal/handler/test_api_tool_handler.py::TestApiToolHandler

4. 运行单个测试方法
pytest test/internal/handler/test_api_tool_handler.py::TestApiToolHandler::test_validate_openapi_schema

5. 通过关键词匹配运行
pytest -k "validate_openapi_schema"

6. 常用附加选项                                                                                             
pytest -v           # 详细输出（已在配置中默认开启）
pytest -s           # 显示 print 输出（已在配置中默认开启）                                                 
pytest --tb=short   # 简化的错误堆栈                      
pytest -x           # 遇到第一个失败就停止
pytest --lf         # 只运行上次失败的测试

由于 pytest.ini 已配置 -v -s，直接运行 pytest 即可看到详细的测试输出和 print 信息。
