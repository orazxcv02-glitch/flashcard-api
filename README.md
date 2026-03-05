# Flashcard E-Learning Platform API

API สำหรับระบบ Flashcard E-Learning Platform รองรับการชำระเงิน PayPal, การซิงค์ข้อมูล และการจัดการคอร์สเรียน

## 🚀 Deploy on Vercel

1. สร้าง Repository บน GitHub และ push code ใน folder `api/` ไปที่ repo
2. Connect Vercel กับ GitHub repo
3. ตั้งค่า Environment Variables ใน Vercel Dashboard

## 🔧 Environment Variables

```bash
SECRET_KEY=your-secret-key
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-role-key
PAYPAL_CLIENT_ID=your-paypal-client-id
PAYPAL_SECRET=your-paypal-secret
PAYPAL_MODE=sandbox
API_BASE_URL=https://your-api.vercel.app
FRONTEND_URL=https://your-username.github.io/forced-learning-app
```

## 📚 API Endpoints

### Authentication
- `POST /api/auth/register` - สมัครสมาชิก
- `POST /api/auth/login` - เข้าสู่ระบบ
- `POST /api/auth/refresh` - Refresh token
- `POST /api/auth/logout` - ออกจากระบบ
- `GET /api/auth/me` - ข้อมูลผู้ใช้

### Courses
- `GET /api/courses` - รายการคอร์สทั้งหมด
- `GET /api/courses/:slug` - รายละเอียดคอร์ส
- `GET /api/courses/:slug/cards` - ข้อมูล flashcard (ต้องมีสิทธิ์)

### User
- `GET /api/user/courses` - คอร์สที่ซื้อแล้ว
- `GET /api/user/profile` - โปรไฟล์ผู้ใช้

### Orders
- `POST /api/orders` - สร้างคำสั่งซื้อ
- `GET /api/orders/:id` - รายละเอียดคำสั่งซื้อ

### Payment
- `POST /api/payment/paypal/create/:order_id` - สร้าง PayPal payment
- `POST /api/payment/paypal/execute/:order_id` - ยืนยันการชำระเงิน

### Sync
- `GET /api/sync/progress` - ดึง progress จาก Cloud
- `POST /api/sync/progress` - อัปโหลด progress
- `POST /api/sync/merge` - Merge conflict

### Admin
- `GET /api/admin/orders` - รายการคำสั่งซื้อทั้งหมด
- `PUT /api/admin/orders/:id` - อัปเดตสถานะคำสั่งซื้อ
- `POST /api/admin/courses` - เพิ่มคอร์สใหม่

## 🛠️ Local Development

```bash
# ติดตั้ง dependencies
pip install -r requirements.txt

# สร้างไฟล์ .env
copy .env.example .env
# แก้ไขค่าใน .env

# รันเซิร์ฟเวอร์
python app.py
```

## 📄 License

MIT License
