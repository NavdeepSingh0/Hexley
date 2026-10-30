# Build the image here, copy it to the server, and restart Hexley (D-058). Keeps the server's token and settings.
# Usage: scripts\deploy\deploy_image.ps1 -Server ubuntu@54.79.105.94 -Domain hexley.site [-Key path] [-Work folder]
param(
  [Parameter(Mandatory = $true)][string]$Server,
  [Parameter(Mandatory = $true)][string]$Domain,
  [string]$Key = "$env:USERPROFILE\.ssh\hexley.pem",
  [string]$Work = $env:TEMP
)
$o = @("-i", $Key, "-o", "ConnectTimeout=20", "-o", "BatchMode=yes")
$tar = Join-Path $Work "hexley-image.tar"
docker build --progress=plain -t hexley:latest . *> (Join-Path $Work "docker_build.log")
if ($LASTEXITCODE -ne 0) { throw "the image did not build; see $Work\docker_build.log" }
docker save hexley:latest -o $tar
python -c "import gzip,shutil,sys; f=open(sys.argv[1],'rb'); g=gzip.open(sys.argv[1]+'.gz','wb',6); shutil.copyfileobj(f,g); g.close(); f.close()" $tar
Remove-Item $tar
scp @o "$tar.gz" "scripts\deploy\ec2_setup.sh" "${Server}:/home/ubuntu/" | Out-Null
ssh @o $Server "sed -i 's/\r$//' ec2_setup.sh; gunzip -c hexley-image.tar.gz | sudo docker load 2>&1 | tail -1; sudo IMAGE=hexley:latest bash ec2_setup.sh $Domain 2>&1 | tail -1; sudo docker image prune -f >/dev/null 2>&1; sudo docker ps --format '{{.Names}} {{.Status}}'; free -m | sed -n 2p"
"public health: " + (curl.exe -s --max-time 40 "https://$Domain/health")
