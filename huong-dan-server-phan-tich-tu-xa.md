title: Hướng dẫn biến máy Windows thành server phân tích từ xa qua SSH
slug: dùng_window_như_server_SSH.html
tag: tag--tools
tag_label: Công cụ phân tích
date: 2026.10.15
reading_time: 10 phút đọc
author: Đào Huy Mạnh
excerpt: Hướng dẫn biến máy Windows thành server phân tích từ xa qua SSH
scripts: 
---
# Hướng dẫn biến máy Windows thành server phân tích từ xa

Tài liệu này tổng hợp các bước đã thực hiện: cài OpenSSH Server trên Windows 11, kết nối từ mạng khác bằng Tailscale, làm việc trong WSL, và giữ máy chạy nền ổn định. Mục tiêu: dùng một máy (server) để chạy phân tích, và điều khiển nó từ máy khác như tablet.

## 1. Tổng quan kiến trúc

- **Máy server**: Windows 11 Pro, bật 24/7, chạy `sshd` và Tailscale dưới dạng service nền.
- **Máy client** (tablet, laptop): có ứng dụng SSH và Tailscale, đăng nhập cùng tài khoản Tailscale.
- **Kết nối**: qua mạng riêng ảo Tailscale, không cần mở port trên router, không cần IP tĩnh, dùng được cả khi bị CGNAT.
- **Công việc**: chạy lệnh PowerShell hoặc Linux (WSL), script Python/R, Jupyter, truyền file.

## 2. Chuẩn bị

- Mở **Windows PowerShell 64-bit** bằng quyền **Administrator** (không dùng bản "(x86)").
- Máy server có Internet.
- Lưu ý PowerShell: `sc` là alias của `Set-Content`, phải gõ `sc.exe`. Khi dán nhiều lệnh, dán từng lệnh một để tránh bị dính dòng.

## 3. Cài OpenSSH Server

### 3.1. Cài đặt

```powershell
Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0
Add-WindowsCapability -Online -Name OpenSSH.Client~~~~0.0.1.0
```

### 3.2. Kiểm tra cài đúng

```powershell
[Environment]::Is64BitProcess
Get-WindowsCapability -Online -Name OpenSSH* | Select Name, State
Test-Path C:\Windows\System32\OpenSSH\sshd.exe
& "C:\Windows\System32\OpenSSH\sshd.exe" -V 2>&1
```

Cài đúng khi capability là `Installed` **và** `sshd.exe` tồn tại. Dòng `NativeCommandError` khi chạy `sshd -V` là bình thường vì phiên bản được in ra stderr.

### 3.3. Xử lý lỗi "Installed nhưng không có sshd.exe"

Triệu chứng đã gặp: capability báo `Installed`, DISM báo Healthy, nhưng thư mục `System32\OpenSSH` không có file. Lệnh `Add-WindowsCapability` lúc này không làm gì vì Windows thấy trạng thái đã là Installed (log CBS ghi `has the same start and target state: Installed, skip planning`).

Cách sửa đã có hiệu quả:

1. Gỡ cả hai capability:
   ```powershell
   Remove-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0
   Remove-WindowsCapability -Online -Name OpenSSH.Client~~~~0.0.1.0
   ```
2. Trạng thái sẽ là `UninstallPending`. **Bắt buộc khởi động lại máy** (`Restart-Computer`), đừng cài lại khi đang `UninstallPending`.
3. Sau reboot, xác nhận cả hai là `NotPresent`:
   ```powershell
   Get-WindowsCapability -Online -Name OpenSSH* | Select Name, State
   ```
4. Cài lại, rồi kiểm tra file:
   ```powershell
   Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0
   Add-WindowsCapability -Online -Name OpenSSH.Client~~~~0.0.1.0
   Test-Path C:\Windows\System32\OpenSSH\sshd.exe
   Test-Path C:\Windows\System32\OpenSSH\ssh.exe
   ```

Nếu vẫn không ra file:

- Dùng DISM với log riêng: `DISM /Online /Add-Capability /CapabilityName:OpenSSH.Server~~~~0.0.1.0 /LogPath:C:\dism-ssh.log`.
- Chạy `DISM /Online /Cleanup-Image /RestoreHealth` rồi `sfc /scannow`.
- Phương án cuối: repair install bằng ISO đúng build, hoặc cài **Win32-OpenSSH** từ GitHub (gỡ capability OpenSSH trước để tránh xung đột service).

Ghi chú: trên máy này `sfc /scannow` báo "could not start the repair service". Việc này chưa được xử lý và không ảnh hưởng SSH, nhưng cho thấy servicing của Windows có vấn đề; nên sửa khi có thời gian.

## 4. Bật dịch vụ sshd

```powershell
Set-Service sshd -StartupType Automatic
Start-Service sshd
Get-Service sshd | Select Name, Status, StartType
```

Tự khởi động lại service nếu bị crash:

```powershell
sc.exe failure sshd reset= 86400 actions= restart/5000/restart/5000/restart/5000
```

Kiểm tra cấu hình và cổng:

```powershell
& "C:\Windows\System32\OpenSSH\sshd.exe" -t
Get-NetTCPConnection -LocalPort 22 -State Listen
Test-NetConnection -ComputerName localhost -Port 22
```

`sshd -t` không in gì nghĩa là cấu hình hợp lệ. `TcpTestSucceeded : True` là đạt.

### Firewall

Cài OpenSSH Server thường tự tạo rule `OpenSSH-Server-In-TCP`. Kiểm tra:

```powershell
Get-NetFirewallRule -Name *ssh* | Select Name, Enabled, Direction, Action
```

Nếu đã có rule này thì **không cần tạo thêm**. Rule tự tạo tên `sshd` với `Profile: Any` là thừa và mở cổng 22 cả trên mạng Public, nên xóa:

```powershell
Remove-NetFirewallRule -Name sshd
```

## 5. Đặt PowerShell làm shell mặc định (tùy chọn)

Mặc định SSH vào Windows dùng `cmd`. Đổi sang PowerShell:

```powershell
New-ItemProperty -Path "HKLM:\SOFTWARE\OpenSSH" -Name DefaultShell -Value "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" -PropertyType String -Force
```

Không nên đặt `wsl.exe` làm shell mặc định: nếu WSL hỏng, bạn sẽ không SSH vào quản trị Windows được. Cứ vào PowerShell rồi gõ `wsl` khi cần.

## 6. Đăng nhập bằng khóa SSH (khuyến nghị)

**Trên máy client** (tạo cặp khóa):

```powershell
ssh-keygen -t ed25519
type $env:USERPROFILE\.ssh\id_ed25519.pub
```

**Trên máy server**, đặt public key tùy loại tài khoản:

- Tài khoản thường: dán vào `C:\Users\TênUser\.ssh\authorized_keys`.
- Tài khoản thuộc nhóm Administrators: dán vào `C:\ProgramData\ssh\administrators_authorized_keys`, rồi chỉnh quyền:
  ```powershell
  icacls C:\ProgramData\ssh\administrators_authorized_keys /inheritance:r /grant "SYSTEM:F" /grant "Administrators:F"
  ```

Kiểm tra đăng nhập bằng khóa thành công **rồi mới** tắt mật khẩu. Sửa `C:\ProgramData\ssh\sshd_config`:

```
PubkeyAuthentication yes
PasswordAuthentication no
```

Sau đó `Restart-Service sshd`. Lưu ý: tài khoản Microsoft đăng nhập SSH bằng mật khẩu tài khoản (không phải PIN); tài khoản không có mật khẩu sẽ không đăng nhập SSH bằng mật khẩu được.

## 7. Kết nối từ mạng khác bằng Tailscale

Tailscale tạo mạng riêng ảo giữa các máy, an toàn hơn nhiều so với mở port ra Internet.

### 7.1. Cài đặt

Trên máy server:

```powershell
winget install --id Tailscale.Tailscale -e
```

Sau đó **mở cửa sổ PowerShell mới**, đăng nhập (`tailscale up` hoặc biểu tượng khay hệ thống). Nếu lệnh `tailscale` không được nhận, gọi bằng đường dẫn đầy đủ: `& "C:\Program Files\Tailscale\tailscale.exe"`.

Trên máy client: cài Tailscale và **đăng nhập cùng tài khoản**.

### 7.2. Lấy địa chỉ và kết nối

```powershell
tailscale status
tailscale ip -4
```

Từ client:

```
ssh tên_user@100.x.y.z
```

### 7.3. Chạy nền, không cần mở cửa sổ

Tailscale chạy bằng Windows service `Tailscale`; biểu tượng khay hệ thống chỉ là giao diện điều khiển.

```powershell
Get-Service Tailscale | Select Name, Status, StartType
Set-Service Tailscale -StartupType Automatic
Start-Service Tailscale
tailscale set --unattended
```

Nếu lệnh `--unattended` không có ở phiên bản của bạn, bật trong giao diện: Preferences, **Run unattended**.

### 7.4. Tắt hết hạn khóa

Vào **login.tailscale.com/admin/machines**, bấm dấu ba chấm cạnh máy server, chọn **Disable key expiry**. Nếu không, máy sẽ mất kết nối khi khóa hết hạn (khoảng 180 ngày).

### 7.5. Nếu SSH bị timeout dù đã có IP Tailscale

Có thể mạng Tailscale bị Windows coi là profile Public và rule firewall không áp dụng. Kiểm tra bằng `Get-NetFirewallRule -Name OpenSSH-Server-In-TCP | Get-NetFirewallProfile` và `Get-NetConnectionProfile`.

## 8. Giữ máy server luôn sẵn sàng

Server phải **bật và có mạng** thì mới kết nối được. Không cần bật màn hình.

```powershell
powercfg /change standby-timeout-ac 0
powercfg /change hibernate-timeout-ac 0
powercfg /change monitor-timeout-ac 10
```

- **Laptop**: đặt đóng nắp là "Do nothing" (Control Panel, Power Options, Choose what closing the lid does), cắm sạc.
- **Mạng**: ưu tiên cáp LAN hơn Wi-Fi.
- **Windows Update** có thể tự khởi động lại máy. `sshd` và Tailscale ở chế độ Automatic sẽ tự lên lại; đặt Active hours để hạn chế reboot giữa giờ làm việc.
- **Mất điện**: vào BIOS bật "Restore on AC Power Loss" thành Power On để máy tự bật khi có điện.
- **BitLocker** kiểu pre-boot PIN sẽ chặn máy ở màn hình nhập PIN; chế độ TPM mặc định thì không.
- **Bật máy từ xa**: Wake-on-LAN chỉ chạy trong LAN, nên qua Tailscale cần một thiết bị luôn bật trong mạng nhà (ví dụ Raspberry Pi) hoặc dùng ổ cắm thông minh.

### Kiểm tra cuối

Khởi động lại server, **không đăng nhập Windows**, chờ 1 đến 2 phút, rồi từ client chạy `ssh tên_user@100.x.y.z`. Kết nối được nghĩa là mọi thứ chạy nền đúng.

## 9. Làm việc trong WSL qua SSH

```powershell
wsl --status
wsl -l -v
wsl --install -d Ubuntu
```

Sau khi cài cần khởi động lại và chạy Ubuntu một lần để tạo user Linux. Distro WSL gắn với từng tài khoản Windows, nên SSH bằng đúng tài khoản đã cài.

Dùng:

```powershell
wsl
wsl -d Ubuntu
wsl ~ -e bash -lc "cd ~/project && python analyze.py"
```

Ghi chú:

- Để code và dữ liệu trong `~/` (hệ file Linux) cho nhanh; ổ C nằm ở `/mnt/c` nhưng chậm hơn.
- Dùng **tmux** (`sudo apt install tmux`) để tác vụ chạy lâu không chết khi tablet mất mạng. Nếu distro vẫn bị tắt khi rảnh, thử thêm vào `C:\Users\TênUser\.wslconfig`: `[wsl2]` và `vmIdleTimeout=-1` (tùy phiên bản WSL mà tùy chọn này có hiệu lực).
- Ứng dụng đồ họa Linux (WSLg) chỉ hiện trên màn hình server, không hiện qua SSH.

## 10. Quy trình phân tích từ xa

### Công cụ trên tablet

- iPad: Termius, Blink Shell.
- Android: Termius, Termux, JuiceSSH.
- Nên dùng bàn phím rời.

### Việc thường làm

- **Chạy script/phân tích**: SSH vào, `wsl`, rồi chạy `python analyze.py` trong tmux.
- **Jupyter hoặc web app trên server**: dùng port forwarding rồi mở trình duyệt trên tablet.
  ```
  ssh -L 8888:localhost:8888 tên_user@100.x.y.z
  ```
  Mở `localhost:8888` trên tablet.
- **Truyền file**: `scp file.csv tên_user@100.x.y.z:~/data/` hoặc dùng SFTP trong Termius.
- **Quản trị Windows**: `Get-Process`, `Get-Service`, `winget upgrade --all`, `Restart-Computer`.
- **Cần giao diện đồ họa**: bật Remote Desktop và kết nối qua IP Tailscale bằng ứng dụng Windows App:
  ```powershell
  Set-ItemProperty 'HKLM:\System\CurrentControlSet\Control\Terminal Server' -Name fDenyTSConnections -Value 0
  Enable-NetFirewallRule -DisplayGroup "Remote Desktop"
  ```

### Hạn chế cần nhớ

- Không mở được ứng dụng đồ họa trên màn hình server qua SSH.
- Tiến trình chạy trong phiên SSH chết khi ngắt kết nối, trừ khi chạy trong tmux, service hoặc Scheduled Task.
- Server tắt hoặc mất mạng thì không vào được.

## 11. Bảo mật

- Chỉ truy cập qua Tailscale, **không** mở port 22 ra Internet. Xóa rule firewall thừa `sshd` (Profile: Any).
- Dùng khóa SSH, tắt đăng nhập bằng mật khẩu sau khi thử khóa thành công.
- Bật 2FA cho tài khoản Tailscale (và nhà cung cấp đăng nhập đi kèm).
- Chỉ cho phép người dùng cần thiết đăng nhập SSH; không dùng chung tài khoản.
- Cập nhật Windows, OpenSSH và Tailscale định kỳ.
- Nếu buộc phải mở port qua router: đổi cổng ngoài, chỉ dùng khóa, và cân nhắc giới hạn nguồn kết nối.

## 12. Checklist hoàn thành

- [ ] `sshd.exe` có trong `C:\Windows\System32\OpenSSH`
- [ ] Service `sshd` Running và Automatic
- [ ] `sshd -t` không báo lỗi, cổng 22 đang Listen
- [ ] Rule firewall chuẩn tồn tại, rule thừa `sshd` đã xóa
- [ ] Đăng nhập bằng khóa SSH thành công, đã tắt mật khẩu
- [ ] Tailscale cài trên cả hai máy, cùng tài khoản, đã Run unattended
- [ ] Đã Disable key expiry cho máy server
- [ ] Sleep/hibernate đã tắt, mạng ổn định
- [ ] Đã thử reboot server không đăng nhập và vẫn SSH vào được
- [ ] WSL cài sẵn, tmux hoạt động (nếu dùng)

## 13. Xử lý sự cố nhanh

| Triệu chứng | Nguyên nhân thường gặp | Cách xử lý |
|---|---|---|
| `Installed` nhưng không có `sshd.exe` | Servicing không triển khai file | Remove, reboot, Add lại (mục 3.3) |
| `sc config ...` báo lỗi `Set-Content` | `sc` là alias PowerShell | Dùng `sc.exe` |
| `tailscale` không được nhận | Chưa cài hoặc PATH chưa cập nhật | Cài, mở PowerShell mới, hoặc gọi đường dẫn đầy đủ |
| SSH timeout qua Tailscale | Firewall profile Public, server tắt/sleep | Kiểm tra profile firewall, `tailscale status`, cài đặt nguồn |
| `Permission denied (publickey)` | Sai vị trí hoặc quyền file `authorized_keys` | Dùng đúng file theo loại tài khoản, chỉnh `icacls` |
| Mất kết nối sau vài tháng | Key expiry của Tailscale | Disable key expiry |
| Tác vụ chết khi ngắt SSH | Tiến trình gắn với phiên | Dùng tmux, service hoặc Scheduled Task |
| `sfc /scannow` không start | Servicing stack lỗi | `DISM /RestoreHealth`, cập nhật Windows, repair install nếu cần |
