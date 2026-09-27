"""配置管理"""
import os
from typing import Optional, Dict, Any
from pydantic import BaseModel

class Config(BaseModel):
    """HelloAgents配置类"""

    # LLM配置
    default_model: str = "gpt-3.5-turbo"
    default_provider: str = "openai"
    temperature: float = 0.7
    max_tokens: Optional[int] = None

    # 系统配置
    debug: bool = False
    log_level: str = "INFO"

    # 其他配置
    max_history_length: int = 100

    """静态构造方法，相当于java的function里面先写函数再内部调构造器，
    public static Config fromEnv() {
        boolean debug = Boolean.parseBoolean(System.getenv("DEBUG"));
        String logLevel = System.getenv("LOG_LEVEL");
        return new Config(debug, logLevel); // 内部调用了构造器
    }
    
    @classmethod 是python常见标注，意思是这是一个class。和java public static一个意思
    
    """


    @classmethod
    def from_env(cls) -> "Config":
        """从环境变量创建配置
        "Config"要加双引号因为这是一个向前引用
        """
        return cls(
            debug=os.getenv("DEBUG", "false").lower() == "true",
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            temperature=float(os.getenv("TEMPERATURE", "0.7")),
            max_tokens=int(os.getenv("MAX_TOKENS")) if os.getenv("MAX_TOKENS") else None,
        )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return self.dict()

