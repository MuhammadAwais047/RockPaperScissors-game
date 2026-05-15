@echo off
powershell -Command "$localBin = \"%USERPROFILE%\.local\bin\"; $userPath = [Environment]::GetEnvironmentVariable('Path', 'User'); if ($userPath -notlike '*\.local\bin*') { [Environment]::SetEnvironmentVariable('Path', \"$userPath;$localBin\", 'User'); echo Added .local\bin to User PATH } else { echo .local\bin already in User PATH }"
