# CloudLens CLI bash completion script
# 手动编写以支持bash 5.3+

_cl_completion() {
    local cur prev opts commands
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"
    
    # 主命令列表
    local main_commands="analyze cache config query remediate dashboard version help"
    
    # analyze子命令
    local analyze_commands="idle renewal cost forecast security tags"
    
    # query子命令
    local query_commands="ecs rds redis vpc slb nas"
    
    # remediate子命令
    local remediate_commands="tags security history"
    
    # 通用选项
    local common_opts="--help --version"
    
    # 根据当前位置提供补全
    case "${COMP_CWORD}" in
        1)
            # 第一个参数：主命令
            COMPREPLY=( $(compgen -W "${main_commands}" -- ${cur}) )
            return 0
            ;;
        2)
            # 第二个参数：子命令
            case "${COMP_WORDS[1]}" in
                analyze)
                    COMPREPLY=( $(compgen -W "${analyze_commands}" -- ${cur}) )
                    ;;
                query)
                    COMPREPLY=( $(compgen -W "${query_commands}" -- ${cur}) )
                    ;;
                remediate)
                    COMPREPLY=( $(compgen -W "${remediate_commands}" -- ${cur}) )
                    ;;
                config)
                    COMPREPLY=( $(compgen -W "add remove list show" -- ${cur}) )
                    ;;
                cache)
                    COMPREPLY=( $(compgen -W "clear list stats" -- ${cur}) )
                    ;;
                *)
                    COMPREPLY=( $(compgen -W "${common_opts}" -- ${cur}) )
                    ;;
            esac
            return 0
            ;;
        *)
            # 其他位置：选项参数
            case "${prev}" in
                --account|-a)
                    # 从配置文件读取账号列表
                    if [ -f ~/.cloudlens/config.json ]; then
                        local accounts=$(python3 -c "import json; f=open('$HOME/.cloudlens/config.json'); data=json.load(f); print(' '.join([a['name'] for a in data.get('accounts',[])]))" 2>/dev/null)
                        COMPREPLY=( $(compgen -W "${accounts}" -- ${cur}) )
                    fi
                    ;;
                --format|-f)
                    COMPREPLY=( $(compgen -W "json csv table excel" -- ${cur}) )
                    ;;
                --days|-d)
                    COMPREPLY=( $(compgen -W "7 14 30 60 90" -- ${cur}) )
                    ;;
                --provider|-p)
                    COMPREPLY=( $(compgen -W "aliyun aws volcengine" -- ${cur}) )
                    ;;
                --region|-r)
                    COMPREPLY=( $(compgen -W "cn-hangzhou cn-beijing cn-shanghai cn-shenzhen" -- ${cur}) )
                    ;;
                *)
                    # 提供常用选项
                    local opts="--account --days --format --output --help --region --provider --trend --cis --confirm"
                    COMPREPLY=( $(compgen -W "${opts}" -- ${cur}) )
                    ;;
            esac
            return 0
            ;;
    esac
}

# 注册completion函数
complete -F _cl_completion cl
