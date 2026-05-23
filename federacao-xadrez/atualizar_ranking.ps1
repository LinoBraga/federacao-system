$link = Read-Host https://s2.chess-results.com/tnr1421231.aspx?lan=10&art=1&SNode=S0
$token = FPBX905432

Write-Host Processando, aguarde... -ForegroundColor Yellow

try {
    $response = Invoke-RestMethod -Uri httpsfpbx-backend.onrender.comadminimport-tournament `
        -Method Post `
        -Headers @{ X-Admin-Token = $token } `
        -ContentType applicationjson; charset=utf-8 `
        -Body (ConvertTo-Json @{ url = $link })

    Write-Host Sucesso! Ranking atualizado. -ForegroundColor Green
    Write-Host $response.message
} catch {
    Write-Host Erro ao atualizar. Verifique o link ou o servidor. -ForegroundColor Red
}

Read-Host Pressione ENTER para sair