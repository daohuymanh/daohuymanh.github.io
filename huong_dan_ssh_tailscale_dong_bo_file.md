title: Hướng dẫn quản lý máy chủ từ xa bằng OpenSSH, Tailscale và đồng bộ file
slug: dung_may_server_client_ssh_tailscale.html
tag: tag--tools
tag_label: Công cụ phân tích
date: 2026.11.05
reading_time: 20 phút đọc
author: Đào Huy Mạnh
excerpt: OpenSSH, Tailscale
scripts: 
---
# Hướng dẫn quản lý máy chủ từ xa bằng OpenSSH, Tailscale và đồng bộ file

## 1. Mục tiêu và mô hình

Tài liệu này hướng dẫn thiết lập kết nối an toàn giữa máy client và máy
server bằng Tailscale, OpenSSH, SCP/SFTP và các phương án đồng bộ file.

Mô hình mục tiêu:

``` text
Máy client (Windows)
    |
    | Tailscale: mạng riêng giữa các thiết bị
    |
    +-- SSH / SCP / SFTP
             |
             v
Máy server (Windows)
    |
    +-- OpenSSH Server
    |
    +-- WSL2: Ubuntu 22.04
    |       +-- Conda / bioinformatics
    |       +-- Docker / Nextflow
    |
    +-- E:\Bioinformatics
            +-- raw_fastq
            +-- references
            +-- projects
            +-- results
            +-- work
            +-- reports
```

**Vai trò của từng công cụ**

  -----------------------------------------------------------------------
  Công cụ                             Công dụng
  ----------------------------------- -----------------------------------
  Tailscale                           Kết nối hai thiết bị qua mạng
                                      riêng, kể cả khi chúng ở các mạng
                                      khác nhau

  OpenSSH                             Đăng nhập và thực thi lệnh từ xa

  SCP                                 Sao chép file qua SSH

  SFTP                                Duyệt và truyền file qua SSH

  rsync                               Đồng bộ tăng dần, phù hợp khi hai
                                      đầu có rsync và shell tương thích

  Git                                 Quản lý phiên bản script, cấu hình
                                      và workflow

  Syncthing (tùy chọn)                Đồng bộ thư mục tự động giữa các
                                      thiết bị
  -----------------------------------------------------------------------

Trong ví dụ, máy server có tên `DESKTOP-O3S35V8`, tài khoản Windows là
`PASTUER HCM`, và thư mục dữ liệu là `E:\Bioinformatics`. Thay các giá
trị này bằng thông tin thực tế nếu khác.

> **An toàn:** Không mở cổng SSH 22 trực tiếp ra Internet nếu không cần
> thiết. Ưu tiên kết nối qua Tailscale và giới hạn quyền truy cập theo
> nhu cầu.

------------------------------------------------------------------------

## 2. Cài đặt và kiểm tra Tailscale

### 2.1. Trên máy server

1.  Cài Tailscale từ trang chính thức: <https://tailscale.com/download>.
2.  Đăng nhập và cho phép thiết bị tham gia tailnet của bạn.
3.  Mở PowerShell và chạy:

``` powershell
tailscale status
tailscale ip -4
```

Ghi lại địa chỉ IPv4 Tailscale của server. Địa chỉ thường thuộc dải
`100.x.x.x`; không dùng địa chỉ ví dụ trong tài liệu thay cho địa chỉ
thực tế.

### 2.2. Trên máy client

1.  Cài Tailscale.
2.  Đăng nhập cùng tailnet, hoặc cấu hình chia sẻ/quyền truy cập phù
    hợp.
3.  Mở PowerShell:

``` powershell
tailscale status
```

Xác nhận máy server xuất hiện trong danh sách.

Nếu không thấy thiết bị, kiểm tra trạng thái đăng nhập, quyền truy cập
tailnet và trạng thái kết nối của cả hai máy.

------------------------------------------------------------------------

## 3. Bật OpenSSH Server trên Windows server

Mở PowerShell **Run as administrator** trên server.

### 3.1. Kiểm tra dịch vụ

``` powershell
Get-Service sshd
```

Nếu OpenSSH Server đã được cài nhưng dịch vụ chưa chạy:

``` powershell
Start-Service sshd
Set-Service -Name sshd -StartupType Automatic
```

Kiểm tra cổng lắng nghe:

``` powershell
Get-NetTCPConnection -LocalPort 22 -State Listen
```

Kiểm tra rule firewall:

``` powershell
Get-NetFirewallRule -Name "OpenSSH-Server-In-TCP" -ErrorAction SilentlyContinue
```

Nếu dịch vụ `sshd` chưa tồn tại, cài tính năng **OpenSSH Server** trong
Windows Settings → System → Optional features → View features, hoặc theo
hướng dẫn Microsoft:
<https://learn.microsoft.com/windows-server/administration/openssh/openssh_install_firstuse>.

### 3.2. Kiểm tra IP và kết nối từ client

Trên server:

``` powershell
tailscale ip -4
```

Trên client, thay `100.x.x.x` bằng IP thực tế:

``` powershell
tailscale ping 100.x.x.x
Test-NetConnection 100.x.x.x -Port 22
```

Nếu `TcpTestSucceeded` là `True`, client có thể tiếp cận cổng SSH. Nếu
không, kiểm tra Tailscale, dịch vụ `sshd` và firewall.

------------------------------------------------------------------------

## 4. SSH từ client vào Windows server

Trên PowerShell của client, chạy:

``` powershell
ssh -l "PASTUER HCM" 100.x.x.x
```

Thay IP bằng địa chỉ Tailscale thật. `-l` giúp xử lý username Windows có
dấu cách.

Lần đầu kết nối, SSH có thể hỏi xác nhận host key. Chỉ chấp nhận sau khi
xác minh đây là máy server của bạn.

Khi đăng nhập thành công, bạn sẽ thấy dấu nhắc Windows, ví dụ:

``` text
pastuer hcm@DESKTOP-O3S35V8 C:\Users\PASTUER HCM>
```

Thoát phiên SSH:

``` text
exit
```

### 4.1. Mở Ubuntu WSL2 từ phiên SSH Windows

Trong phiên SSH, xem tên bản phân phối:

``` powershell
wsl --list --verbose
```

Nếu Ubuntu mới có tên `Ubuntu-22.04`:

``` powershell
wsl -d Ubuntu-22.04
```

Kiểm tra hệ điều hành bên trong Ubuntu:

``` bash
lsb_release -a
```

Có thể chạy một lệnh Ubuntu mà không mở shell tương tác:

``` powershell
wsl -d Ubuntu-22.04 -- bash -lc "lsb_release -a"
```

Thay `Ubuntu-22.04` bằng tên thực tế trong danh sách nếu khác.

**Lưu ý:** Cách này đăng nhập SSH vào Windows trước rồi mới mở Ubuntu.
Nếu cần SSH trực tiếp vào Ubuntu, phải cài và cấu hình `openssh-server`
trong Ubuntu, đồng thời xử lý địa chỉ mạng và khả năng truy cập WSL2
riêng.

------------------------------------------------------------------------

## 5. Sao chép file bằng SCP

SCP truyền file qua SSH. Các ví dụ sau chạy trên PowerShell của client.

### 5.1. Gửi một file lên thư mục home của tài khoản Windows server

Ví dụ file trên client là `C:\Data\sample_sheet.csv`:

``` powershell
scp "C:\Data\sample_sheet.csv" "PASTUER HCM@100.x.x.x:"
```

File được gửi vào thư mục mặc định của tài khoản Windows trên server.

### 5.2. Tải file từ server về client

``` powershell
scp "PASTUER HCM@100.x.x.x:C:/Users/PASTUER HCM/Documents/result.csv" "C:\Data\"
```

Cách diễn giải đường dẫn Windows có thể phụ thuộc shell mặc định của
OpenSSH. Nếu đường dẫn có dấu cách hoặc đường dẫn ổ đĩa gây lỗi, dùng
SFTP hoặc kiểm tra cấu hình shell và đường dẫn của server.

### 5.3. Gửi cả thư mục nhỏ

``` powershell
scp -r "C:\Data\Project1" "PASTUER HCM@100.x.x.x:"
```

`-r` cho phép sao chép đệ quy thư mục.

### 5.4. Lưu ý khi truyền dữ liệu sinh tin

-   Thử trước bằng một file nhỏ.
-   Với FASTQ lớn, kiểm tra checksum sau khi truyền.
-   SCP thường không thuận tiện để tiếp tục một lần truyền lớn bị gián
    đoạn.
-   Không ghi đè FASTQ gốc hoặc xóa dữ liệu gốc chỉ vì bản sao đã được
    gửi.
-   Không nên giả định đường dẫn `E:/Bioinformatics/...` sẽ hoạt động
    giống nhau trong mọi shell OpenSSH trên Windows. Xác nhận bằng một
    thử nghiệm nhỏ trước khi truyền hàng trăm GB.

------------------------------------------------------------------------

## 6. Truyền file bằng SFTP

SFTP cung cấp phiên làm việc tương tác để duyệt và truyền file.

Trên PowerShell của client:

``` powershell
sftp -l "PASTUER HCM" 100.x.x.x
```

Các lệnh thường dùng bên trong dấu nhắc SFTP:

  Lệnh              Chức năng
  ----------------- ----------------------------------
  `pwd`             Xem thư mục hiện tại trên server
  `lpwd`            Xem thư mục hiện tại trên client
  `ls`              Liệt kê file phía server
  `lls`             Liệt kê file phía client
  `cd <path>`       Đổi thư mục phía server
  `lcd <path>`      Đổi thư mục phía client
  `put file.csv`    Gửi một file lên server
  `get file.csv`    Tải một file về client
  `put -r folder`   Gửi thư mục
  `get -r folder`   Tải thư mục
  `exit`            Thoát SFTP

Ví dụ:

``` text
lcd C:/Data
put sample_sheet.csv
```

Để truyền thư mục lớn trên ổ E:, trước tiên kiểm tra cách SFTP hiển thị
và truy cập ổ đĩa Windows trên máy chủ. Không nên giả định đường dẫn ổ
đĩa có cú pháp Linux.

------------------------------------------------------------------------

## 7. Đồng bộ file và thư mục

Copy file và đồng bộ là hai việc khác nhau. Đồng bộ thường so sánh nội
dung hiện có rồi chỉ truyền các thay đổi cần thiết.

### 7.1. Dùng rsync giữa hai đầu Linux/WSL

Nếu cả client và server đều có `rsync`, và SSH kết nối trực tiếp tới
shell Linux tương thích, cài rsync trên cả hai đầu:

``` bash
sudo apt update
sudo apt install -y rsync
```

Gửi nội dung thư mục báo cáo lên server Linux:

``` bash
rsync -avh --progress ./reports/ user@server:/path/to/reports/
```

Tải kết quả về client:

``` bash
rsync -avh --progress user@server:/path/to/results/ ./results/
```

Ý nghĩa:

-   `-a`: lưu cấu trúc thư mục và các thuộc tính phù hợp.
-   `-v`: hiển thị chi tiết.
-   `-h`: hiển thị dung lượng dễ đọc.
-   `--progress`: hiển thị tiến độ truyền.

Dấu `/` cuối `./reports/` có nghĩa là đồng bộ **nội dung** thư mục đó.

**Quan trọng:** SSH vào Windows OpenSSH không có nghĩa là phiên SSH đó
hỗ trợ `rsync`. Các lệnh trên phù hợp khi SSH tới Linux/WSL có `rsync`
và shell tương thích. Để dùng rsync xuyên qua Windows server, cần thiết
kế đường truyền và môi trường thực thi riêng; hãy thử với dữ liệu mẫu
trước.

### 7.2. Dùng Robocopy giữa hai máy Windows

`robocopy` phù hợp để đồng bộ thư mục Windows khi thư mục đích được truy
cập qua ổ đĩa hoặc đường dẫn mạng đã cấu hình, chẳng hạn SMB.

Ví dụ tổng quát:

``` powershell
robocopy "C:\Data\Reports" "\\SERVER\Share\Reports" /E /Z /R:2 /W:5
```

Trong đó:

-   `/E`: sao chép các thư mục con, kể cả thư mục rỗng.
-   `/Z`: chế độ sao chép có thể tiếp tục sau gián đoạn.
-   `/R:2`: thử lại tối đa 2 lần.
-   `/W:5`: chờ 5 giây giữa các lần thử.

Đây là ví dụ yêu cầu bạn đã cấu hình chia sẻ SMB và quyền truy cập.
Tailscale không tự tạo ra đường dẫn chia sẻ mạng.

**Không thêm `/MIR` một cách tùy tiện.** Tùy chọn này phản chiếu thư mục
nguồn sang đích và có thể xóa file ở đích nếu file đó không còn trong
nguồn.

### 7.3. Đồng bộ tự động bằng Syncthing (tùy chọn)

Syncthing có thể đồng bộ thư mục tự động giữa các thiết bị:
<https://syncthing.net/>.

Tailscale cung cấp kết nối riêng; Syncthing đảm nhiệm việc phát hiện và
truyền thay đổi trong các thư mục được cấu hình.

Với dữ liệu FASTQ gốc, nên cân nhắc thiết lập thư mục nguồn ở chế độ chỉ
đọc hoặc chọn chế độ truyền một chiều phù hợp, đồng thời giữ bản sao dự
phòng. Không cấu hình đồng bộ hai chiều cho dữ liệu quan trọng nếu chưa
hiểu rõ cách xử lý xóa file và xung đột.

------------------------------------------------------------------------

## 8. Thiết lập SSH key để đăng nhập thuận tiện hơn

SSH key giúp hạn chế việc nhập mật khẩu tài khoản Windows nhiều lần.
Private key phải được giữ bí mật.

### 8.1. Tạo key trên client

Trong PowerShell của client:

``` powershell
ssh-keygen -t ed25519
```

Chấp nhận đường dẫn mặc định hoặc chọn đường dẫn riêng. Nên đặt
passphrase cho private key.

Xem public key:

``` powershell
Get-Content "$env:USERPROFILE\.ssh\id_ed25519.pub"
```

Chỉ sao chép nội dung của file `.pub` để thêm vào `authorized_keys` trên
server. **Không chia sẻ file `id_ed25519` không có phần mở rộng** vì đó
là private key.

### 8.2. Cấu hình `authorized_keys` trên Windows

Vị trí file và quyền truy cập phụ thuộc loại tài khoản Windows. Với tài
khoản thông thường, file thường nằm trong:

``` text
C:\Users\<username>\.ssh\authorized_keys
```

Với tài khoản thuộc nhóm Administrators, OpenSSH trên Windows có thể sử
dụng file quản trị viên riêng được khai báo trong `sshd_config`, thường
là:

``` text
C:\ProgramData\ssh\administrators_authorized_keys
```

Không nên tự chọn vị trí trước khi kiểm tra cấu hình thực tế. Tham khảo
tài liệu chính thức:
<https://learn.microsoft.com/windows-server/administration/openssh/openssh-server-configuration>.

Sau khi cấu hình public key và quyền file đúng, thử lại từ client:

``` powershell
ssh -l "PASTUER HCM" 100.x.x.x
```

Nếu không thành công, kiểm tra log OpenSSH và cấu hình `sshd_config`;
đừng tắt xác thực mật khẩu trước khi xác nhận key hoạt động.

------------------------------------------------------------------------

## 9. Tổ chức dữ liệu sinh tin trên server

Đề xuất cấu trúc trên ổ E::

``` text
E:\Bioinformatics\
├── raw_fastq\       # FASTQ gốc, không chỉnh sửa
├── references\      # Genome tham chiếu, primer BED, annotation
├── projects\        # Script, workflow và cấu hình
├── results\         # Kết quả cuối, consensus, báo cáo QC
├── work\            # File trung gian của workflow
└── reports\         # Báo cáo phục vụ kiểm tra và viết bài
```

Quy tắc thực hành:

1.  Giữ FASTQ gốc bất biến sau khi tiếp nhận.
2.  Tính checksum SHA-256 trước hoặc sau khi truyền để xác minh dữ liệu.
3.  Quản lý script và workflow bằng Git.
4.  Không đồng bộ hoặc sao lưu file trung gian dung lượng lớn nếu không
    cần thiết.
5.  Không xóa thư mục `work` khi Nextflow còn đang chạy.
6.  Giữ ít nhất một bản sao dự phòng độc lập cho dữ liệu quan trọng;
    RAID hoặc đồng bộ không thay thế backup.
7.  Hạn chế quyền truy cập vào dữ liệu mẫu và thông tin có thể nhận diện
    bệnh nhân.

### Kiểm tra checksum trên Windows

Tạo checksum cho một file:

``` powershell
Get-FileHash "C:\Data\sample.fastq.gz" -Algorithm SHA256
```

Trên server, chạy lại với file đã nhận:

``` powershell
Get-FileHash "E:\Bioinformatics\raw_fastq\sample.fastq.gz" -Algorithm SHA256
```

Hai giá trị SHA-256 phải giống nhau. Có thể lưu checksum vào manifest để
kiểm tra về sau.

------------------------------------------------------------------------

## 10. Quản lý tác vụ Nextflow qua SSH

Sau khi SSH vào Windows server và mở Ubuntu WSL2:

``` powershell
wsl -d Ubuntu-22.04
```

Trong Ubuntu, vào môi trường workflow:

``` bash
conda activate workflow
nextflow -version
```

Chạy pipeline với log được lưu lại:

``` bash
mkdir -p /mnt/e/Bioinformatics/reports/logs
```

Ví dụ lệnh chạy một pipeline:

``` bash
nextflow run main.nf \
  -profile docker \
  -work-dir /mnt/e/Bioinformatics/work/example_run \
  -with-report /mnt/e/Bioinformatics/reports/logs/example_report.html \
  -with-timeline /mnt/e/Bioinformatics/reports/logs/example_timeline.html \
  -with-trace /mnt/e/Bioinformatics/reports/logs/example_trace.txt
```

Đây là ví dụ tổng quát. Tùy pipeline, bạn cần bổ sung các tham số đầu
vào và cấu hình thích hợp. Không chạy nguyên ví dụ nếu chưa xác định
đúng file `main.nf`, profile và các tham số bắt buộc.

Nếu cần tác vụ tiếp tục sau khi phiên SSH ngắt, dùng `tmux` trong
Ubuntu:

``` bash
tmux new -s viralrecon
```

Chạy pipeline bên trong phiên `tmux`. Để tách phiên mà không dừng tác
vụ, nhấn `Ctrl+B`, sau đó nhấn `D`.

Kết nối lại:

``` bash
tmux attach -t viralrecon
```

`tmux` giúp duy trì phiên terminal khi SSH ngắt, nhưng không bảo đảm tác
vụ tiếp tục nếu Windows tắt, WSL bị dừng hoặc máy mất điện. Với tác vụ
dài ngày, cần quản lý nguồn điện, trạng thái WSL và log.

------------------------------------------------------------------------

## 11. Khắc phục sự cố thường gặp

### SSH báo timeout hoặc không kết nối được

Trên client:

``` powershell
tailscale status
tailscale ping 100.x.x.x
Test-NetConnection 100.x.x.x -Port 22
```

Trên server:

``` powershell
Get-Service sshd
Get-NetTCPConnection -LocalPort 22 -State Listen
```

Kiểm tra Tailscale đang đăng nhập đúng tailnet, dịch vụ SSH đang chạy và
firewall không chặn kết nối.

### SSH báo sai mật khẩu

-   Xác nhận đúng username Windows.
-   Với username có dấu cách, dùng `ssh -l "PASTUER HCM" 100.x.x.x`.
-   Kiểm tra phương thức xác thực được phép trong OpenSSH.
-   Không gửi mật khẩu hoặc private key qua tin nhắn.

### SCP không tìm thấy đường dẫn ổ E:

-   Thử truyền file vào thư mục home trước.
-   Dùng SFTP để kiểm tra đường dẫn.
-   Xác nhận shell mặc định và cách OpenSSH trên Windows xử lý đường dẫn
    ổ đĩa.
-   Không truyền dữ liệu lớn cho tới khi thử nghiệm với file nhỏ thành
    công.

### Docker không chạy trong Ubuntu WSL2

Kiểm tra Docker Desktop đang chạy và WSL Integration đã bật cho đúng bản
Ubuntu mới. Trong Ubuntu:

``` bash
docker --version
docker info
```

Nếu lệnh `docker` không tồn tại, bật tích hợp WSL trong Docker Desktop
trước khi cài một Docker Engine khác.

### rsync không hoạt động

Xác nhận cả hai đầu có `rsync` và SSH kết nối tới môi trường shell tương
thích. `rsync` không tự hoạt động qua mọi cấu hình OpenSSH trên Windows.

------------------------------------------------------------------------

## 12. Checklist triển khai

-   [ ] Tailscale được cài và đăng nhập trên cả client và server.
-   [ ] Client nhìn thấy server trong `tailscale status`.
-   [ ] OpenSSH Server trên Windows đặt tự khởi động.
-   [ ] `Test-NetConnection <IP_Tailscale> -Port 22` thành công.
-   [ ] SSH đăng nhập đúng tài khoản Windows.
-   [ ] Từ SSH Windows có thể mở đúng Ubuntu WSL2.
-   [ ] SCP/SFTP truyền được file nhỏ theo cả hai chiều.
-   [ ] Checksum SHA-256 khớp sau khi truyền.
-   [ ] SSH key hoạt động trước khi thay đổi chính sách xác thực.
-   [ ] Thư mục dữ liệu sinh tin được tổ chức rõ ràng.
-   [ ] Đã có kế hoạch backup độc lập.
-   [ ] Pipeline dài được theo dõi qua log và `tmux` hoặc cơ chế quản lý
    tác vụ phù hợp.

## Tài liệu chính thức

-   Tailscale Downloads: <https://tailscale.com/download>
-   Tailscale SSH: <https://tailscale.com/docs/features/tailscale-ssh>
-   Microsoft OpenSSH:
    <https://learn.microsoft.com/windows-server/administration/openssh/openssh-overview>
-   Cấu hình OpenSSH Server trên Windows:
    <https://learn.microsoft.com/windows-server/administration/openssh/openssh-server-configuration>
-   Syncthing: <https://syncthing.net/>
-   Docker Desktop với WSL2:
    <https://docs.docker.com/desktop/features/wsl/>
