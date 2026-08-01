# M1 真联调冒烟测试（curl 脚本化，结果可复现）
# 约定：后端全局异常处理器统一返回 HTTP 200，业务成败由 body.code 判定，
#       故所有断言基于 body.code，而非 HTTP 状态码。
# 运行：pwsh code/infra/scripts/smoke_test.ps1  （需后端已在 127.0.0.1:8000 运行）
$ErrorActionPreference = "Stop"
$base = "http://127.0.0.1:8000"
$fail = 0
$actor = 1   # dev-token 主体 id，与审计 actor_id 对齐

function Assert-Code {
  param($resp, $expect, $name)
  try { $j = $resp | ConvertFrom-Json }
  catch { Write-Output "FAIL $name : 响应非 JSON -> $resp"; $global:fail++; return $null }
  $code = $j.code
  if ($code -eq $expect) {
    Write-Output "PASS $name : code=$code"
  } else {
    Write-Output "FAIL $name : 期望 code=$expect, 实际 code=$code msg=$($j.message)"
    $global:fail++
  }
  return $j
}

# 0) 前置探活：根路径 /health（非 /api/v1/health），真实探测 Redis/PostgreSQL
$hc = curl.exe -s -o $null -w "%{http_code}" "$base/health"
if ($hc -ne "200") { Write-Output "FAIL: 后端未就绪 /health -> HTTP $hc"; exit 1 }
Write-Output "HEALTH_OK"

# 1) 拿 platform 角色 dev-token
$tok = (curl.exe -s -X POST "$base/api/v1/auth/dev-token" -H "Content-Type: application/json" -d "{\"role\":\"platform\",\"sub\":\"$actor\"}" | ConvertFrom-Json).data.access_token
if (-not $tok) { Write-Output "FAIL: 无法获取 dev-token"; exit 1 }
$h = "Authorization: Bearer $tok"
Write-Output "TOKEN_OK len=$($tok.Length)"

# 2) 患者列表
$j = Assert-Code (curl.exe -s "$base/api/v1/ih/users" -H $h) 0 "GET /ih/users"
if ($j) { Write-Output "  total=$($j.data.total) users" }

# 3) 医师审核 approve（取列表第一个待审 doctor_id）
$dl = curl.exe -s "$base/api/v1/ih/doctors?status=pending" -H $h | ConvertFrom-Json
$did = $dl.data.items[0].id
if (-not $did) { Write-Output "SKIP /ih/doctors approve (无待审医师)" }
else {
  $j = Assert-Code (curl.exe -s -X POST "$base/api/v1/ih/doctors/$did/approve" -H $h -H "Content-Type: application/json" -d "{\"action\":\"approve\",\"reviewer_id\":$actor}") 0 "POST /ih/doctors/$did/approve"
  if ($j) { Write-Output "  status=$($j.data.status)" }
}

# 4) 合规提交（需 category/subject_type/title）
$j = Assert-Code (curl.exe -s -X POST "$base/api/v1/plat/compliance/submit" -H $h -H "Content-Type: application/json" -d '{"category":"privacy","subject_type":"platform","title":"联调测试","content_json":{"k":"v"}}') 0 "POST /plat/compliance/submit"
if ($j) { Write-Output "  id=$($j.data.id) status=$($j.data.status)" }

# 5) 自包含闭环：先开方（造一张待审处方），再审核，再凭方下单
$rxj = Assert-Code (curl.exe -s -X POST "$base/api/v1/ih/prescriptions" -H $h -H "Content-Type: application/json" -d "{\"patient_id\":1,\"doctor_id\":1,\"diagnose\":\"smoke\",\"items\":[{\"name\":\"布洛芬\",\"spec\":\"0.3g\",\"dosage\":\"口服\",\"freq\":\"qd\",\"qty\":1}]}") 0 "POST /ih/prescriptions (开方)"
$rxid = if ($rxj) { $rxj.data.id } else { $null }
Write-Output "  new rx id=$rxid status=$($rxj.data.status)"

# 6) 处方审核 audit（取刚开的处方）
if (-not $rxid) { Write-Output "SKIP audit (开方失败)" }
else {
  $j = Assert-Code (curl.exe -s -X PATCH "$base/api/v1/ih/prescriptions/$rxid/audit" -H $h -H "Content-Type: application/json" -d "{\"action\":\"approve\",\"reviewer_id\":$actor}") 0 "PATCH /ih/prescriptions/$rxid/audit"
  if ($j) { Write-Output "  status=$($j.data.status)" }
}

# 7) R4 处方药凭方：不带 prescription_id 应被拦截（业务码 1001，HTTP 仍为 200）
$j = curl.exe -s -X POST "$base/api/v1/ih/orders" -H $h -H "Content-Type: application/json" -d '{"user_id":1,"type":"rx","amount":100}' | ConvertFrom-Json
if ($j.code -eq 1001 -and $null -eq $j.data) {
  Write-Output "PASS R4-拦截: code=$($j.code) msg=$($j.message)"
} else {
  Write-Output "FAIL R4-拦截: 期望 code=1001/data=null, 实际 code=$($j.code) data=$($j.data)"
  $fail++
}

# 8) R4 处方药凭方：带 prescription_id 应成功，且回显 prescription_id
#    凭方语义：rx 订单必须关联一张真实存在且已 approved 的处方，复用第 6 步审核通过的处方 id。
if (-not $rxid) { Write-Output "FAIL R4-放行: 无可用处方，无法验证凭方下单"; $fail++ }
else {
  $j = curl.exe -s -X POST "$base/api/v1/ih/orders" -H $h -H "Content-Type: application/json" -d "{\"user_id\":1,\"type\":\"rx\",\"amount\":100,\"prescription_id\":$rxid}" | ConvertFrom-Json
  if ($j.code -eq 0 -and $j.data.prescription_id -eq $rxid) {
    Write-Output "PASS R4-放行: order_no=$($j.data.order_no) prescription_id=$($j.data.prescription_id)"
  } else {
    Write-Output "FAIL R4-放行: 期望 code=0 且回显 prescription_id=$rxid, 实际 code=$($j.code) msg=$($j.message)"
    $fail++
  }
}

# 9) 问诊/排班列表
$j = Assert-Code (curl.exe -s "$base/api/v1/ih/consultations" -H $h) 0 "GET /ih/consultations"
if ($j) { Write-Output "  total=$($j.data.total) consults" }
$j = Assert-Code (curl.exe -s "$base/api/v1/ih/schedules" -H $h) 0 "GET /ih/schedules"
if ($j) { Write-Output "  total=$($j.data.total) schedules" }

Write-Output "=== SMOKE DONE (fail=$fail) ==="
exit $fail
