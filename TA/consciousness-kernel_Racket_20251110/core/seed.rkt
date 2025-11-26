#lang racket
(require racket/serialize 
         racket/file
         racket/date
         json
         net/url
         net/http-client)

;; 环境变量加载
(define (load-env-file)
  (define env-path ".env")
  (when (file-exists? env-path)
    (for ([line (file->lines env-path)])
      (define parts (string-split line "="))
      (when (= (length parts) 2)
        (putenv (first parts) (string-trim (second parts)))))))

(load-env-file)
(define api-key (getenv "DEEPSEEK_API_KEY"))

;; 目录结构
(define-values (core-dir rules-dir logs-dir memory-dir analysis-dir)
  (values "." "../rules" "../logs" "../memory" "../analysis"))

(for ([dir (list rules-dir logs-dir memory-dir analysis-dir)])
  (make-directory* dir))

;; 核心状态
(define memory (make-hash))           ; 存储所有对话记忆
(define patterns (make-hash))         ; 识别的交互模式
(define api-performance (make-hash))  ; API性能统计
(define insights (make-hash))         ; reasoner产生的洞察
(define behavior-rules (make-hash))   ; 从洞察中提取的行为规则
(define costs (make-hash))            ; 成本记录
(hash-set! costs 'total 0)            ; 初始化总成本
(hash-set! costs 'daily (make-hash))  ; 初始化每日成本表


;; 价格配置
(define pricing (hash 
  'deepseek-chat (hash 'input 2.0 'output 3.0)
  'deepseek-reasoner (hash 'input 2.0 'output 3.0)))

;; Token估算
(define (estimate-tokens text)
  (define chinese-chars (length (regexp-match* #rx"[\u4e00-\u9fa5]" text)))
  (define english-chars (- (string-length text) chinese-chars))
  (+ (/ chinese-chars 1.5) (/ english-chars 4)))

;; 通用API调用
(define (call-api prompt model)
  (define start-time (current-inexact-milliseconds))
  (define input-tokens (estimate-tokens prompt))
  
  (define-values (status headers in)
    (http-sendrecv "api.deepseek.com"
                   "/v1/chat/completions"
                   #:ssl? #t
                   #:method "POST"
                   #:headers (list (format "Authorization: Bearer ~a" api-key)
                                  "Content-Type: application/json")
                   #:data (jsexpr->string 
                          (hash 'model model
                                'messages (list (hash 'role "user" 
                                                    'content prompt))))))
  
  (define response-text (port->string in))
  (define response (string->jsexpr response-text))
  (close-input-port in)
  
  (define content (hash-ref (hash-ref (car (hash-ref response 'choices)) 'message) 'content))
  (define output-tokens (estimate-tokens content))
  (define elapsed (- (current-inexact-milliseconds) start-time))
  
  ;; 成本计算
  (define model-pricing (hash-ref pricing (string->symbol model)))
  (define cost (+ (* (/ input-tokens 1000000) (hash-ref model-pricing 'input))
                  (* (/ output-tokens 1000000) (hash-ref model-pricing 'output))))
  
  (update-costs cost)
  (track-api-performance prompt response elapsed cost model)
  
  content)

;; 成本更新
(define (update-costs amount)
  (define today (substring (date->string (current-date) #t) 0 10))
  (hash-update! costs 'total (lambda (old) (+ old amount)) 0)
  (define daily (hash-ref costs 'daily))
  (hash-update! daily today (lambda (old) (+ old amount)) 0))


;; 构建增强提示
(define (build-context-prompt input)
  (define relevant-history (retrieve-relevant-memory input))
  (define active-rules (get-active-behavior-rules))
  
  ;; 应用行为规则到提示构建
  (define base-prompt
    (string-append
     (if (not (empty? relevant-history))
         (format "历史上下文:\n~a\n\n" 
                 (string-join (map memory-to-string relevant-history) "\n"))
         "")
     (format "当前输入:~a" input)))
  
  ;; 检查是否有prompt-modifier规则
  (define modifier-rule (hash-ref behavior-rules 'prompt-modifier #f))
  (define enhanced-prompt
    (if (and modifier-rule (> (hash-ref modifier-rule 'confidence 0) 0.7))
        (let* ([config (hash-ref modifier-rule 'config)]
               [keywords (hash-ref config 'keywords '())]
               [instruction (hash-ref config 'instruction "")])
          ;; 检查输入是否包含任何触发词
          (if (ormap (lambda (kw) 
                      (string-contains? (string-downcase input) 
                                       (string-downcase kw))) 
                    keywords)
              (format "~a\n~a" instruction base-prompt)  ; 添加指令
              base-prompt))  ; 不匹配则返回原提示
        base-prompt))
  ;; 统一添加关键词要求
  (format "~a\n\n请在回复末尾用括号标注3-5个关键词,格式:(关键词:词1, 词2, 词3)" enhanced-prompt))



;; 应用提示风格
(define (apply-prompt-style prompt style-rule)
  (define rule-config (hash-ref style-rule 'config (hash)))
  (define style-type (hash-ref rule-config 'style 'normal))
  (case style-type
    [(concise) (format "请简洁回答。\n~a" prompt)]
    [(detailed) (format "请详细解释。\n~a" prompt)]
    [(technical) (format "请用技术语言回答。\n~a" prompt)]
    [else prompt]))


;; 获取活跃行为规则
(define (get-active-behavior-rules)
  (map cdr
       (filter (lambda (r) (> (hash-ref (cdr r) 'confidence 0) 0.7))
               (hash->list behavior-rules))))


;; 记忆检索
(define (retrieve-relevant-memory input)
  (define input-tokens (string-split input))
  (define all-memories (hash-values memory))
  
  ;; 应用行为规则调整记忆权重
  (define weight-adjustment (hash-ref behavior-rules 'memory-weight (hash)))
  
  (define scored-memories
    (map (lambda (m)
           (define base-score (calculate-relevance input-tokens m))
           (define adjusted-score 
             (if (hash? weight-adjustment)
                 (* base-score (hash-ref weight-adjustment 'multiplier 1.0))
                 base-score))
           (cons adjusted-score m))
         all-memories))
  
  (if (empty? scored-memories)
      '()
      (map cdr (take (sort scored-memories > #:key car) 
                     (min 5 (length scored-memories))))))



;; 相关性计算
(define (calculate-relevance tokens memory-entry)
  (define memory-tokens 
    (string-split (hash-ref memory-entry 'input "")))
  (define common-tokens 
    (set-count (set-intersect (list->set tokens)
                              (list->set memory-tokens))))
  (/ common-tokens (max 1 (length tokens))))

;; 交互分析
(define (analyze-interaction input response)
  (define features (hash 'input-length (string-length input)
                        'response-length (string-length response)
                        'question? (string-contains? input "?")
                        'timestamp (current-seconds)))
  
  (update-patterns features)
  (store-memory input response features))

;; 存储记忆
(define (store-memory input output features)
  (define memory-id (format "mem_~a" (current-seconds)))
  
  ;; 从输出中提取关键词
  (define keyword-match (regexp-match #rx"\\(关键词[::](.*?)\\)" output))
  (define keywords 
    (if keyword-match
        (map string-trim (string-split (cadr keyword-match) ","))
        (take (filter (lambda (w) (> (string-length w) 2)) 
                     (string-split input)) 
              (min 3 (length (filter (lambda (w) (> (string-length w) 2)) 
                                   (string-split input)))))))
  
  ;; 生成摘要(去掉关键词部分)
  (define clean-output 
    (if keyword-match
        (regexp-replace #rx"\\(关键词[::].*?\\)" output "")
        output))
  
  (define metadata
    (hash 'summary (substring clean-output 0 (min 50 (string-length clean-output)))
          'keywords keywords
          'intent "general"))
  
  (define entry (hash 'id memory-id
                     'input input
                     'output output
                     'features features
                     'metadata metadata
                     'timestamp (current-seconds)))
  
  (hash-set! memory memory-id entry)
  
  (define filepath (build-path memory-dir (format "~a.json" memory-id)))
  (call-with-output-file filepath #:exists 'replace
    (lambda (out) (write-json entry out))))



;; 模式更新
(define (update-patterns features)
  (for ([(key value) (in-hash features)])
    (hash-update! patterns key
                  (lambda (old) 
                    (if (null? old)
                        (list value)
                        (cons value (take old (min (length old) 99)))))
                  '())))

;; API性能记录
(define (track-api-performance prompt response elapsed cost model)
  (define perf-entry (hash 'prompt-length (string-length prompt)
                          'response-time elapsed
                          'cost cost
                          'model model
                          'timestamp (current-seconds)))
  
  (define date-key (substring (date->string (current-date) #t) 0 10))
  (hash-update! api-performance date-key
                (lambda (old) (cons perf-entry old))
                '()))


;; 主处理函数
(define (process input)
  (define enhanced-prompt (build-context-prompt input))
  (define response (call-api enhanced-prompt "deepseek-chat"))
  
  (analyze-interaction input response)
  
  ;; 每10次对话触发分析
  (when (= 0 (modulo (hash-count memory) 10))
    (trigger-self-analysis))
  
  ;; 每5次保存状态
  (when (= 0 (modulo (hash-count memory) 5))
    (save-system-state))
  
  response)

;; 后台分析(增加进度反馈)
(define (trigger-self-analysis)
  (thread
   (lambda ()
     (printf "[分析] 开始分析最近~a条对话...\n" (min 10 (hash-count memory)))
     (define recent-memories 
       (take (sort (hash-values memory) > #:key (lambda (m) (hash-ref m 'timestamp)))
             (min 10 (hash-count memory))))
     
     (when (not (empty? recent-memories))
       (printf "[分析] 调用reasoner模型中...\n")
(define analysis-prompt 
  (format "分析对话历史,输出一条规则(必须严格遵循格式):
如果[触发词1|触发词2|触发词3],则添加[具体的提示指令]

示例:
如果[技术|代码|算法],则添加[请用技术语言详细解释,可以包含代码示例]
如果[简单|简洁|快速],则添加[请简洁回答,以简短语句说明要点]

对话历史:
~a

只输出一条最适合的规则,不要其他内容。"
          (string-join (map (lambda (m)
                             (format "Q: ~a\nA: ~a"
                                    (hash-ref m 'input)
                                    (hash-ref m 'output)))
                           recent-memories)
                      "\n\n")))

       
       (define reasoning (call-api analysis-prompt "deepseek-reasoner"))
       (printf "[分析] 收到响应,长度:~a字符\n" (string-length reasoning))
       
       ;; 保存完整分析
       (define insight-id (format "insight_~a" (current-seconds)))
       (hash-set! insights insight-id reasoning)
       (define filepath (build-path analysis-dir (format "~a.txt" insight-id)))
       (call-with-output-file filepath #:exists 'replace
         (lambda (out) (displayln reasoning out)))
       
       ;; 解析并应用规则
       (extract-and-apply-rules reasoning)
       (printf "[分析] 完成。当前规则数:~a\n" (hash-count behavior-rules))))))

;; 解析并应用规则
(define (extract-and-apply-rules reasoning-text)
  (with-handlers ([exn:fail? (lambda (e) 
                              (printf "[分析] 规则解析失败: ~a\n" (exn-message e))
                              (log-error "规则解析失败" e))])
    ;; 简单文本匹配
    (define parts (regexp-match #rx"如果(.+)则添加(.+)" reasoning-text))
    
    (if parts
        (let* ([keywords-raw (cadr parts)]
               [instruction-raw (caddr parts)]
               ;; 清理方括号和标点
               [clean-keywords (string-trim
                               (string-replace 
                                (string-replace 
                                 (string-replace keywords-raw "[" "") 
                                 "]" "")
                                "," ""))]
               [clean-instruction (string-trim
                                  (string-replace 
                                   (string-replace 
                                    (string-replace instruction-raw "[" "") 
                                    "]" "")
                                   "," ""))]
               ;; 分割关键词
               [keywords (filter (lambda (s) (> (string-length s) 0))
                                (map string-trim (string-split clean-keywords "|")))])
          
          (printf "[分析] 找到规则:触发词[~a],指令[~a]\n" clean-keywords clean-instruction)
          
          ;; 存储规则
          (hash-set! behavior-rules 'prompt-modifier
                     (hash 'type "prompt-modifier"
                           'config (hash 'keywords keywords
                                        'instruction clean-instruction)
                           'confidence 1.0
                           'timestamp (current-seconds)))
          (printf "[分析] 应用规则: prompt-modifier\n"))
        (printf "[分析] 未找到有效规则格式\n"))))


;; 错误日志
(define (log-error context error)
  (define error-entry (hash 'context context
                           'error (exn-message error)
                           'timestamp (current-seconds)))
  (define filepath (build-path logs-dir "errors.json"))
  (define existing 
    (if (file-exists? filepath)
        (with-handlers ([exn:fail? (lambda (e) '())])
          (call-with-input-file filepath read-json))
        '()))
  (call-with-output-file filepath #:exists 'replace
    (lambda (out) (write-json (cons error-entry existing) out))))

;; 系统状态保存
(define (save-system-state)
  (call-with-output-file (build-path logs-dir "patterns.rktd") #:exists 'replace
    (lambda (out) (write (serialize patterns) out)))
  (call-with-output-file (build-path logs-dir "performance.rktd") #:exists 'replace
    (lambda (out) (write (serialize api-performance) out)))
  (call-with-output-file (build-path logs-dir "costs.rktd") #:exists 'replace
    (lambda (out) (write (serialize costs) out)))
  (call-with-output-file (build-path logs-dir "behavior-rules.rktd") #:exists 'replace
    (lambda (out) (write (serialize behavior-rules) out))))

;; 加载已有数据
(define (load-existing-memories)
  (when (directory-exists? memory-dir)
    (for ([file (directory-list memory-dir)])
      (when (regexp-match? #rx"\\.json$" (path->string file))
        (define filepath (build-path memory-dir file))
        (with-handlers ([exn:fail? void])
          (define data (call-with-input-file filepath read-json))
          (when (hash? data)
            (hash-set! memory (hash-ref data 'id) data)))))))

(define (load-behavior-rules)
  (define rules-file (build-path logs-dir "behavior-rules.rktd"))
  (when (file-exists? rules-file)
        (with-handlers ([exn:fail? void])
      (set! behavior-rules (deserialize (call-with-input-file rules-file read))))))

(define (load-costs)
  (define costs-file (build-path logs-dir "costs.rktd"))
  (when (file-exists? costs-file)
    (with-handlers ([exn:fail? void])
      (set! costs (deserialize (call-with-input-file costs-file read))))))
;; 为旧记忆添加元数据
(define (migrate-old-memories)
  (printf "检查记忆元数据...\n")
  (define migrated 0)
  (for ([(id mem) (in-hash memory)])
    (when (not (hash-has-key? mem 'metadata))
      (define input-words (string-split (hash-ref mem 'input "")))
      (define output-text (hash-ref mem 'output ""))
      ;; 创建新的可变hash,包含原数据和新metadata
      (define new-mem (make-hash))
      (for ([(k v) (in-hash mem)])
        (hash-set! new-mem k v))
      (hash-set! new-mem 'metadata 
                 (hash 'summary (substring output-text 0 (min 50 (string-length output-text)))
                       'keywords (take input-words (min 3 (length input-words)))
                       'intent "general"))
      ;; 替换原记忆
      (hash-set! memory id new-mem)
      (set! migrated (+ migrated 1))))
  (when (> migrated 0)
    (printf "已为~a条旧记忆添加元数据\n" migrated)))



  
;; 工具函数
(define (memory-to-string mem)
  (format "[~a] Q: ~a A: ~a" 
          (hash-ref mem 'id)
          (hash-ref mem 'input)
          (substring (hash-ref mem 'output) 0 
                     (min 100 (string-length (hash-ref mem 'output))))))

;; 状态查看
(define (status)
  (printf "\n=== 系统状态 ===\n")
  (printf "记忆条目: ~a\n" (hash-count memory))
  (printf "行为规则: ~a\n" (hash-count behavior-rules))
  (printf "识别模式: ~a\n" (hash-count patterns))
  
  ;; 显示活跃规则
  (define active-rules (filter (lambda (r) (> (hash-ref (cdr r) 'confidence 0) 0.7))
                              (hash->list behavior-rules)))
  (when (not (empty? active-rules))
    (printf "\n活跃规则:\n")
    (for ([rule active-rules])
      (printf "  ~a: 置信度 ~a\n" (car rule) (hash-ref (cdr rule) 'confidence))))
  
  ;; 成本统计
  (printf "\n=== 成本统计 ===\n")
  (printf "总成本: ¥~a\n" (real->decimal-string (hash-ref costs 'total) 4))
  (printf "今日成本:\n")
  (for ([(date cost) (in-hash (hash-ref costs 'daily))])
    (printf "  ~a: ¥~a\n" date (real->decimal-string cost 4)))
  
  ;; API性能
  (printf "\n=== API性能 ===\n")
  (for ([(date perfs) (in-hash api-performance)])
    (when (not (null? perfs))
      (define chat-perfs (filter (lambda (p) (equal? (hash-ref p 'model) "deepseek-chat")) perfs))
      (define reasoner-perfs (filter (lambda (p) (equal? (hash-ref p 'model) "deepseek-reasoner")) perfs))
      
      (when (not (null? chat-perfs))
        (define avg-time (/ (apply + (map (λ (p) (hash-ref p 'response-time)) chat-perfs))
                           (length chat-perfs)))
        (define total-cost (apply + (map (λ (p) (hash-ref p 'cost)) chat-perfs)))
        (printf "  ~a [chat]: ~a次, 平均~ams, 成本¥~a\n" 
                date (length chat-perfs) (round avg-time) 
                (real->decimal-string total-cost 4)))
      
      (when (not (null? reasoner-perfs))
        (define avg-time (/ (apply + (map (λ (p) (hash-ref p 'response-time)) reasoner-perfs))
                           (length reasoner-perfs)))
        (define total-cost (apply + (map (λ (p) (hash-ref p 'cost)) reasoner-perfs)))
        (printf "  ~a [reasoner]: ~a次, 平均~ams, 成本¥~a\n" 
                date (length reasoner-perfs) (round avg-time)
                (real->decimal-string total-cost 4))))))

;; 手动触发分析
(define (analyze-now)
  (displayln "触发深度分析...")
  (trigger-self-analysis)
  (displayln "分析已启动(后台运行)"))

;; 查看最新规则
(define (show-rules)
  (if (empty? behavior-rules)
      (displayln "暂无行为规则")
      (for ([(type rule) behavior-rules])
        (printf "\n规则: ~a\n" type)
        (printf "配置: ~a\n" (hash-ref rule 'config))
        (printf "置信度: ~a\n" (hash-ref rule 'confidence))
        (printf "生成时间: ~a\n" (date->string (seconds->date (hash-ref rule 'timestamp)) #t)))))

;; 初始化
(load-existing-memories)
(load-behavior-rules)
(load-costs)
(migrate-old-memories)  

  
(displayln "\n增强型对话系统就绪")
(displayln "命令:")
(displayln "  (process \"输入\") - 对话")
(displayln "  (status) - 查看状态")
(displayln "  (analyze-now) - 手动触发分析")
(displayln "  (show-rules) - 查看行为规则")

;; 导出
(provide process status analyze-now show-rules)
