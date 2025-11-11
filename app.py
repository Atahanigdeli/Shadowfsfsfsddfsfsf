import time
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ecommerce.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Database Models
import os
from werkzeug.utils import secure_filename

# Configure upload folder and allowed extensions
UPLOAD_FOLDER = 'static/uploads/profile_pics'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # 2MB max file size

# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    address = db.Column(db.String(200))
    phone = db.Column(db.String(20))
    profile_pic = db.Column(db.String(200))
    
    def set_password(self, password):
        # Use a consistent hashing method with a fixed salt
        self.password_hash = generate_password_hash(
            password,
            method='pbkdf2:sha256',
            salt_length=16
        )
        
    def check_password(self, password):
        # Check password using the same hashing method
        return check_password_hash(self.password_hash, password)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text)
    image_url = db.Column(db.String(200))

class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Lütfen giriş yapın.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route('/')
def index():
    # Sample rental products
    rental_products = [
        {
            'id': 1,
            'name': 'Araç Kiralama Sistemi',
            'price': 1499.99,
            'description': 'Profesyonel araç kiralama web sitesi çözümü',
            'image_url': 'https://img.freepik.com/free-vector/car-rental-concept-illustration_114360-1021.jpg'
        },
        {
            'id': 2,
            'name': 'Ofis Kiralama Platformu',
            'price': 1999.99,
            'description': 'Esnek ofis ve çalışma alanı kiralama sistemi',
            'image_url': 'https://img.freepik.com/free-vector/hand-drawn-coworking-illustration_23-2149350884.jpg'
        },
        {
            'id': 3,
            'name': 'Ekipman Kiralama Sistemi',
            'price': 1299.99,
            'description': 'Her türlü ekipman için kiralama çözümü',
            'image_url': 'https://img.freepik.com/free-vector/construction-tools-realistic-composition_1284-26007.jpg'
        },
        {
            'id': 4,
            'name': 'Tatil Evi Kiralama',
            'price': 1799.99,
            'description': 'Tatil evi ve villa kiralama platformu',
            'image_url': 'https://img.freepik.com/free-vector/vacation-rentals-concept-illustration_114360-1020.jpg'
        }
    ]
    return render_template('index.html', products=rental_products)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        if User.query.filter_by(username=username).first():
            flash('Bu kullanıcı adı zaten alınmış.', 'danger')
            return redirect(url_for('register'))
            
        if User.query.filter_by(email=email).first():
            flash('Bu e-posta adresi zaten kullanılıyor.', 'danger')
            return redirect(url_for('register'))
            
        user = User(username=username, email=email)
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        flash('Kayıt başarılı! Giriş yapabilirsiniz.', 'success')
        return redirect(url_for('login'))
        
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user:
            if user.check_password(password):
                session['user_id'] = user.id
                session['username'] = user.username
                session['email'] = user.email
                if user.profile_pic:
                    session['profile_pic'] = url_for('static', filename=f'uploads/profile_pics/{user.profile_pic}')
                flash('Başarıyla giriş yapıldı!', 'success')
                return redirect(url_for('profile'))
            else:
                # Debug: Print hashed password for troubleshooting
                print(f"Login attempt failed for user: {username}")
                print(f"Stored hash: {user.password_hash}")
                print(f"Input password: {password}")
        
        flash('Geçersiz kullanıcı adı veya şifre.', 'danger')
            
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    flash('Başarıyla çıkış yapıldı.', 'success')
    return redirect(url_for('index'))

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    user = User.query.get(session['user_id'])
    
    if request.method == 'POST':
        user.email = request.form['email']
        user.address = request.form['address']
        user.phone = request.form['phone']
        
        db.session.commit()
        flash('Profil bilgileriniz güncellendi.', 'success')
        return redirect(url_for('profile'))
        
    return render_template('profile.html', user=user)

@app.route('/profile/picture', methods=['GET', 'POST'])
@login_required
def profile_picture():
    if request.method == 'POST':
        # Check if the post request has the file part
        if 'profile_pic' not in request.files:
            flash('Dosya seçilmedi', 'danger')
            return redirect(request.url)
        
        file = request.files['profile_pic']
        
        # If user does not select file, browser also
        # submit an empty part without filename
        if file.filename == '':
            flash('Dosya seçilmedi', 'danger')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            user = User.query.get(session['user_id'])
            
            # Delete old profile picture if exists
            if user.profile_pic and os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], user.profile_pic)):
                try:
                    os.remove(os.path.join(app.config['UPLOAD_FOLDER'], user.profile_pic))
                except Exception as e:
                    print(f"Error deleting old profile picture: {e}")
            
            # Save new profile picture
            filename = f"user_{user.id}_{int(time.time())}.{file.filename.rsplit('.', 1)[1].lower()}"
            filename = secure_filename(filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            
            # Update user profile picture in database
            user.profile_pic = filename
            db.session.commit()
            
            # Update session
            session['profile_pic'] = url_for('static', filename=f'uploads/profile_pics/{filename}')
            
            flash('Profil resmi başarıyla güncellendi!', 'success')
            return redirect(url_for('profile'))
        else:
            flash('İzin verilen dosya türleri: png, jpg, jpeg, gif', 'danger')
    
    return render_template('profile_picture.html')

# Serve uploaded files
@app.route('/static/uploads/profile_pics/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/change_password', methods=['POST'])
@login_required
def change_password():
    print("Change password route called")  # Debug log
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        print(f"Current password: {current_password}")  # Debug log
        print(f"New password: {new_password}")  # Debug log
        print(f"Confirm password: {confirm_password}")  # Debug log
        
        # Basic validation
        if not all([current_password, new_password, confirm_password]):
            flash('Lütfen tüm alanları doldurunuz.', 'danger')
            return redirect(url_for('profile'))
            
        if len(new_password) < 8:
            flash('Yeni şifre en az 8 karakter uzunluğunda olmalıdır.', 'danger')
            return redirect(url_for('profile'))
            
        if not any(char.isdigit() for char in new_password) or \
           not any(char.isupper() for char in new_password) or \
           not any(char.islower() for char in new_password):
            flash('Yeni şifre en az bir büyük harf, bir küçük harf ve bir rakam içermelidir.', 'danger')
            return redirect(url_for('profile'))
            
        if new_password != confirm_password:
            flash('Yeni şifreler eşleşmiyor.', 'danger')
            return redirect(url_for('profile'))
        
        user = User.query.get(session['user_id'])
        
        if not user.check_password(current_password):
            flash('Mevcut şifre yanlış.', 'danger')
        else:
            try:
                user.set_password(new_password)
                db.session.commit()
                flash('Şifreniz başarıyla değiştirildi.', 'success')
                print("Password changed successfully")  # Debug log
            except Exception as e:
                db.session.rollback()
                flash('Bir hata oluştu. Lütfen tekrar deneyiniz.', 'danger')
                app.logger.error(f'Password change error: {str(e)}')
                print(f"Error changing password: {str(e)}")  # Debug log
    
    return redirect(url_for('profile'))

@app.route('/add_to_cart/<int:product_id>')
@login_required
def add_to_cart(product_id):
    cart_item = Cart.query.filter_by(user_id=session['user_id'], product_id=product_id).first()
    
    if cart_item:
        cart_item.quantity += 1
    else:
        cart_item = Cart(user_id=session['user_id'], product_id=product_id)
        db.session.add(cart_item)
    
    db.session.commit()
    flash('Ürün sepete eklendi.', 'success')
    return redirect(url_for('index'))

@app.route('/cart')
@login_required
def cart():
    cart_items = db.session.query(Cart, Product).join(Product).filter(Cart.user_id == session['user_id']).all()
    total = sum(item.Product.price * item.Cart.quantity for item in cart_items)
    return render_template('cart.html', cart_items=cart_items, total=total)

@app.route('/remove_from_cart/<int:cart_id>', methods=['POST'])
@login_required
def remove_from_cart(cart_id):
    # Make sure the cart item belongs to the current user
    cart_item = Cart.query.filter_by(id=cart_id, user_id=session['user_id']).first()
    if cart_item:
        db.session.delete(cart_item)
        db.session.commit()
        flash('Ürün sepetinizden kaldırıldı.', 'success')
    else:
        flash('Ürün bulunamadı veya silinemedi.', 'danger')
    return redirect(url_for('cart'))

@app.route('/clear_cart', methods=['POST'])
@login_required
def clear_cart():
    # Delete all cart items for the current user
    Cart.query.filter_by(user_id=session['user_id']).delete()
    db.session.commit()
    flash('Sepetiniz boşaltıldı.', 'success')
    return redirect(url_for('cart'))

@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    # Get user data
    user = User.query.get(session['user_id'])
    
    # Get cart items and calculate total
    cart_items = db.session.query(Cart, Product).join(Product).filter(Cart.user_id == session['user_id']).all()
    total = sum(item.Product.price * item.Cart.quantity for item in cart_items)
    
    if request.method == 'POST':
        # Process payment here (simplified)
        card_number = request.form.get('card_number', '').strip()
        expiry = request.form.get('expiry', '').strip()
        cvv = request.form.get('cvv', '').strip()
        
        # Basic validation
        if not all([card_number, expiry, cvv]):
            flash('Lütfen tüm ödeme bilgilerini doldurun.', 'danger')
            return redirect(url_for('checkout'))
            
        # In a real app, you would process the payment here
        # This is just a simplified example
        
        # Clear the cart after successful payment
        Cart.query.filter_by(user_id=session['user_id']).delete()
        db.session.commit()
        
        flash('Siparişiniz alındı! Teşekkür ederiz.', 'success')
        return redirect(url_for('index'))
        
    return render_template('checkout.html', user=user, total=total, cart_items=cart_items)

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        subject = request.form.get('subject')
        message = request.form.get('message')
        
        # Here you would typically save this to a database or send an email
        # For now, we'll just show a success message
        
        flash('Mesajınız başarıyla gönderildi. En kısa sürede size dönüş yapılacaktır.', 'success')
        return redirect(url_for('contact'))
        
    return render_template('contact.html')

# Kiralama Sayfası
@app.route('/kiralama')
def kiralama():
    # Sample rental services data
    rental_services = [
        {
            'id': 1,
            'name': 'Araç Kiralama Sistemi',
            'price': 1499.99,
            'description': 'Profesyonel araç kiralama web sitesi çözümü',
            'image_url': 'https://img.freepik.com/free-vector/car-rental-concept-illustration_114360-1021.jpg',
            'features': ['Sınırsız araç ekleyin', 'Rezervasyon takvimi', 'Ödeme entegrasyonu']
        },
        {
            'id': 2,
            'name': 'Ofis Kiralama Platformu',
            'price': 1999.99,
            'description': 'Esnek ofis ve çalışma alanı kiralama sistemi',
            'image_url': 'https://img.freepik.com/free-vector/hand-drawn-coworking-illustration_23-2149350884.jpg',
            'features': ['Çoklu ofis yönetimi', 'Online rezervasyon', 'Müşteri yönetim paneli']
        },
        {
            'id': 3,
            'name': 'Ekipman Kiralama Sistemi',
            'price': 1299.99,
            'description': 'Her türlü ekipman için kiralama çözümü',
            'image_url': 'https://img.freepik.com/free-vector/construction-tools-realistic-composition_1284-26007.jpg',
            'features': ['Stok takibi', 'Kiralama takvimi', 'Bakım bildirimleri']
        },
        {
            'id': 4,
            'name': 'Tatil Evi Kiralama',
            'price': 1799.99,
            'description': 'Tatil evi ve villa kiralama platformu',
            'image_url': 'https://img.freepik.com/free-vector/vacation-rentals-concept-illustration_114360-1020.jpg',
            'features': ['Çoklu mülk yönetimi', 'Rezervasyon takvimi', 'Ödeme entegrasyonu']
        }
    ]
    return render_template('kiralama.html', services=rental_services)

# Discord Bot Page
@app.route('/discord-bot')
def discord_bot():
    return render_template('discord-bot.html')

# Bot Komutları Sayfası
@app.route('/bot-komutlari')
def bot_komutlari():
    return render_template('bot-komutlari.html')

# Web Hizmetleri Sayfası
@app.route('/web-hizmetleri')
def web_hizmetleri():
    return render_template('web-hizmetleri.html')

# Discord Bot Kiralama Sayfası
@app.route('/discord-bot-kiralama')
def discord_bot_kiralama():
    return render_template('discord-bot-kiralama.html')

# Category and Featured Routes
@app.route('/kategori/<category_slug>')
def category(category_slug):
    # In a real app, you would filter products by category
    # For now, we'll just show all products
    products = Product.query.all()
    category_name = category_slug.replace('-', ' ').title()
    return render_template('category.html', products=products, category_name=category_name)

@app.route('/indirimdekiler')
def discounted_products():
    # In a real app, you would filter discounted products
    products = Product.query.all()  # This should be filtered for discounted items
    return render_template('featured.html', 
                         products=products, 
                         title='İndirimdeki Ürünler',
                         description='En iyi fırsatlar ve indirimli ürünler burada!')

@app.route('/yeni-gelenler')
def new_arrivals():
    # In a real app, you would filter new arrivals
    products = Product.query.order_by(Product.id.desc()).limit(8).all()
    return render_template('featured.html', 
                         products=products, 
                         title='Yeni Gelenler',
                         description='En yeni ürünlerimizi keşfedin!')

@app.route('/coksatanlar')
def bestsellers():
    # In a real app, you would filter bestsellers
    products = Product.query.order_by(Product.id).limit(8).all()  # This should be ordered by sales
    return render_template('featured.html', 
                         products=products, 
                         title='Çok Satanlar',
                         description='En çok tercih edilen ürünlerimiz')

@app.route('/firsat-urunleri')
def special_offers():
    # In a real app, you would filter special offers
    products = Product.query.limit(8).all()  # This should be filtered for special offers
    return render_template('featured.html', 
                         products=products, 
                         title='Fırsat Ürünleri',
                         description='Sınırlı süreli fırsatlar')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Add some sample products if none exist
        if not Product.query.first():
            products = [
                Product(name='Ürün 1', price=99.99, description='Harika bir ürün', image_url='https://via.placeholder.com/200'),
                Product(name='Ürün 2', price=149.99, description='İkinci harika ürün', image_url='https://via.placeholder.com/200'),
                Product(name='Ürün 3', price=199.99, description='Üçüncü harika ürün', image_url='https://via.placeholder.com/200'),
            ]
            db.session.add_all(products)
            db.session.commit()
    app.run(debug=True)
