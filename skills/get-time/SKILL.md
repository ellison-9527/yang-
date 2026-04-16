---
name: get-time
description: 获取当前时间、当前日期、时区时间、时间戳、北京时间、本地时间的技能。当用户提到“现在几点”“当前时间”“帮我看下北京时间”“给我一个时间戳”“换算某个时区的当前时间”等与获取当前时间有关的请求时，优先使用此 skill，即使用户只是用口语化表达询问现在的时间。
enable: True
---

# Get Time

用于获取和返回当前时间信息。

## 实现要求
- 使用 JavaScript 获取时间，不再依赖其他语言实现。
- 优先使用 `node` 执行内联 JavaScript。
- 不要手算时间，必须通过系统时间与 JS 标准库获取。
- 涉及时区时，优先使用 `Intl.DateTimeFormat`。

## 适用场景
当用户需要以下内容时使用本技能：
- 当前本地时间
- 当前日期
- 指定时区当前时间
- Unix 时间戳
- 北京时间 / UTC 时间

## 工作步骤
1. 先识别用户要的时间类型：
   - 普通当前时间
   - 当前日期
   - 指定时区时间
   - 时间戳
2. 使用 `node -e` 执行 JavaScript 获取准确时间。
3. 若用户指定时区，则使用 `Intl.DateTimeFormat` 或 `toLocaleString` 配合 `timeZone` 输出。
4. 输出尽量简洁清晰；如果用户没指定格式，可同时给出：
   - 日期
   - 时间
   - 时区

## 推荐实现方式
### 1) 获取本地当前时间
```bash
node -e "const d=new Date(); const pad=n=>String(n).padStart(2,'0'); console.log(`${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`)"
```

### 2) 获取 Unix 时间戳（秒）
```bash
node -e "console.log(Math.floor(Date.now()/1000))"
```

### 3) 获取指定时区时间
```bash
node -e "const tz='Asia/Shanghai'; const d=new Date(); const fmt=new Intl.DateTimeFormat('zh-CN',{timeZone:tz,year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:false}); console.log(`${tz}: ${fmt.format(d).replace(/\//g,'-')}`)"
```

### 4) 获取 UTC 时间
```bash
node -e "console.log(new Date().toISOString())"
```

## 输出格式
默认使用下面的简洁格式：

- 当前时间：YYYY-MM-DD HH:MM:SS
- 时区：<timezone>
- Unix 时间戳：<timestamp>

如果用户只要其中一项，就只返回该项。

## 示例
**示例 1**  
用户：现在几点？  
输出：当前时间：2025-01-01 14:23:45

**示例 2**  
用户：帮我看下北京时间  
输出：北京时间：2025-01-01 14:23:45 (Asia/Shanghai)

**示例 3**  
用户：给我一个当前 unix 时间戳  
输出：Unix 时间戳：1735712625

## 注意事项
- 不要编造时间，必须调用系统能力获取。
- 如果 `node` 不可用，再明确说明无法执行，而不是伪造结果。
- 若时区不明确，默认说明当前系统时区。
- 若用户要求多种格式，可同时返回多种表示。
