from flask import Flask, render_template, request, jsonify, session, redirect, url_for, Response
from flask_cors import CORS
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime, timedelta
import os
import json
from functools import wraps
import csv
import io

app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)

# Configuration
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['ADMIN_USERNAME'] = os.getenv('ADMIN_USERNAME')
app.config['ADMIN_PASSWORD'] = os.getenv('ADMIN_PASSWORD')  # Change this!

# MongoDB connection (lazy initialization for serverless)
MONGO_URI = os.getenv('MONGO_URI')
DB_NAME = os.getenv('DB_NAME')
client = None
db = None
invoices_collection = None
users_collection = None

def ensure_db() -> bool:
    global client, db, invoices_collection, users_collection
    if invoices_collection is not None and users_collection is not None:
        return True
    try:
        if not MONGO_URI:
            print("MONGO_URI is not set.")
            return False
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        invoices_collection = db.invoices
        users_collection = db.users
        print("Connected to MongoDB successfully!")
        return True
    except Exception as e:
        print(f"Error connecting to MongoDB: {e}")
        return False


def convert_mongo_document(doc):
    """Convert MongoDB document to JSON-serializable format"""
    if doc is None:
        return None
    
    if isinstance(doc, list):
        return [convert_mongo_document(item) for item in doc]
    
    if isinstance(doc, dict):
        result = {}
        for key, value in doc.items():
            if isinstance(value, ObjectId):
                result[key] = str(value)
            elif isinstance(value, datetime):
                result[key] = value.isoformat()
            elif isinstance(value, dict):
                result[key] = convert_mongo_document(value)
            elif isinstance(value, list):
                result[key] = convert_mongo_document(value)
            else:
                result[key] = value
        return result
    
    return doc


class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super(JSONEncoder, self).default(obj)


app.json_encoder = JSONEncoder


# Authentication decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session or not session['logged_in']:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def require_db(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not ensure_db():
            return jsonify({'success': False, 'error': 'Database not configured or unreachable. Set MONGO_URI and DB_NAME.'}), 500
        return f(*args, **kwargs)
    return decorated_function


# Favicon handlers (serve from /static)
@app.route('/favicon.ico')
def favicon_ico():
    return redirect(url_for('static', filename='favicon.ico'))


@app.route('/favicon.png')
def favicon_png():
    return redirect(url_for('static', filename='favicon.png'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Handle both form data and JSON
        if request.content_type and 'application/json' in request.content_type:
            data = request.get_json()
            username = data.get('username')
            password = data.get('password')
        else:
            username = request.form.get('username')
            password = request.form.get('password')
        
        if username == app.config['ADMIN_USERNAME'] and password == app.config['ADMIN_PASSWORD']:
            session['logged_in'] = True
            session['username'] = username
            return jsonify({'success': True, 'message': 'Login successful'}), 200
        else:
            return jsonify({'success': False, 'error': 'Invalid username or password'}), 401
    
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/')
@login_required
def index():
    return render_template('index.html')


@app.route('/api/invoices', methods=['GET'])
@login_required
@require_db
def get_invoices():
    try:
        # Get month filter from query params
        month_filter = request.args.get('month')
        year_filter = request.args.get('year')
        
        query = {}
        if month_filter and year_filter:
            try:
                month = int(month_filter)
                year = int(year_filter)
                start_date = datetime(year, month, 1)
                if month == 12:
                    end_date = datetime(year + 1, 1, 1)
                else:
                    end_date = datetime(year, month + 1, 1)
                
                # Query for invoices where date field matches the month/year
                # Primary: check the 'date' field
                # Fallback: check 'created_at' if 'date' doesn't exist
                query = {
                    '$or': [
                        {
                            'date': {
                                '$gte': start_date,
                                '$lt': end_date
                            }
                        },
                        {
                            '$and': [
                                {'date': {'$exists': False}},
                                {'created_at': {
                                    '$gte': start_date,
                                    '$lt': end_date
                                }}
                            ]
                        }
                    ]
                }
            except Exception as e:
                print(f"Error in date filtering: {e}")
                import traceback
                traceback.print_exc()
                pass
        # Status filtering
        if status_filter:
            if status_filter == 'overdue':
                # Overdue: past due date AND not paid
                today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                query['$and'] = query.get('$and', [])
                query['$and'].extend([
                    {'payment_due_date': {'$lt': today}},
                    {'status': {'$ne': 'paid'}}
                ])
            else:
                # Paid or pending
                query['status'] = status_filter
        
        invoices = list(invoices_collection.find(query).sort('created_at', -1))

        # Convert MongoDB documents to JSON-serializable format
        invoices_json = convert_mongo_document(invoices)
        return jsonify({'success': True, 'data': invoices_json}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/invoices', methods=['POST'])
@login_required
@require_db
def create_invoice():
    try:
        if request.is_json:
            data = request.get_json() or {}
        else:
            data = request.form.to_dict()
        
        # Parse amount if provided
        if 'amount' in data:
            try:
                data['amount'] = float(data['amount'])
            except:
                data['amount'] = 0.0
        
        # Parse dates
        if 'date' in data and data['date']:
            try:
                data['date'] = datetime.strptime(data['date'], '%Y-%m-%d')
            except:
                data['date'] = datetime.now()
        else:
            data['date'] = datetime.now()
        
        if 'payment_due_date' in data and data['payment_due_date']:
            try:
                data['payment_due_date'] = datetime.strptime(data['payment_due_date'], '%Y-%m-%d')
            except:
                pass
        
        # Add timestamps
        data['created_at'] = datetime.now()
        data['updated_at'] = datetime.now()
        
        result = invoices_collection.insert_one(data)
        invoice = invoices_collection.find_one({'_id': result.inserted_id})
        
        # Convert MongoDB document to JSON-serializable format
        invoice_json = convert_mongo_document(invoice)
        
        return jsonify({'success': True, 'data': invoice_json}), 201
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/invoices/<invoice_id>', methods=['GET'])
@login_required
@require_db
def get_invoice(invoice_id):
    try:
        invoice = invoices_collection.find_one({'_id': ObjectId(invoice_id)})
        if invoice:
            # Convert MongoDB document to JSON-serializable format
            invoice_json = convert_mongo_document(invoice)
            return jsonify({'success': True, 'data': invoice_json}), 200
        return jsonify({'success': False, 'error': 'Invoice not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/invoices/<invoice_id>', methods=['PUT'])
@login_required
@require_db
def update_invoice(invoice_id):
    try:
        # Handle both JSON and form data
        if request.content_type and 'application/json' in request.content_type:
            data = request.get_json() or {}
        else:
            data = request.form.to_dict()
        
        # Parse amount if provided
        if 'amount' in data:
            try:
                data['amount'] = float(data['amount'])
            except:
                pass
        
        # Parse dates
        if 'date' in data and data['date']:
            try:
                data['date'] = datetime.strptime(data['date'], '%Y-%m-%d')
            except:
                pass
        
        if 'payment_due_date' in data and data['payment_due_date']:
            try:
                data['payment_due_date'] = datetime.strptime(data['payment_due_date'], '%Y-%m-%d')
            except:
                pass
        
        data['updated_at'] = datetime.now()
        
        result = invoices_collection.update_one(
            {'_id': ObjectId(invoice_id)},
            {'$set': data}
        )
        
        if result.modified_count > 0:
            invoice = invoices_collection.find_one({'_id': ObjectId(invoice_id)})
            # Convert MongoDB document to JSON-serializable format
            invoice_json = convert_mongo_document(invoice)
            return jsonify({'success': True, 'data': invoice_json}), 200
        return jsonify({'success': False, 'error': 'Invoice not found or no changes made'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/invoices/<invoice_id>', methods=['DELETE'])
@login_required
@require_db
def delete_invoice(invoice_id):
    try:
        result = invoices_collection.delete_one({'_id': ObjectId(invoice_id)})
        
        if result.deleted_count > 0:
            return jsonify({'success': True, 'message': 'Invoice deleted successfully'}), 200
        return jsonify({'success': False, 'error': 'Invoice not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/invoices/monthly', methods=['GET'])
@login_required
@require_db
def get_monthly_invoices():
    try:
        # Get all invoices grouped by month
        pipeline = [
            {
                '$group': {
                    '_id': {
                        'year': {'$year': '$date'},
                        'month': {'$month': '$date'}
                    },
                    'count': {'$sum': 1},
                    'total_amount': {'$sum': '$amount'},
                    'invoices': {'$push': '$$ROOT'}
                }
            },
            {'$sort': {'_id.year': -1, '_id.month': -1}}
        ]
        
        monthly_data = list(invoices_collection.aggregate(pipeline))
        # Convert MongoDB documents to JSON-serializable format
        monthly_data_json = convert_mongo_document(monthly_data)
        return jsonify({'success': True, 'data': monthly_data_json}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/invoices/export/csv', methods=['GET'])
@login_required
@require_db
def export_invoices_csv():
    try:
        # Get month filter from query params if provided
        month_filter = request.args.get('month')
        year_filter = request.args.get('year')
        
        query = {}
        if month_filter and year_filter:
            try:
                month = int(month_filter)
                year = int(year_filter)
                start_date = datetime(year, month, 1)
                if month == 12:
                    end_date = datetime(year + 1, 1, 1)
                else:
                    end_date = datetime(year, month + 1, 1)
                query['$or'] = [
                    {'date': {'$gte': start_date, '$lt': end_date}},
                    {'created_at': {'$gte': start_date, '$lt': end_date}}
                ]
            except:
                pass
        
        # Get all invoices
        invoices = list(invoices_collection.find(query).sort('created_at', -1))
        
        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'Invoice Number',
            'Client Name',
            'Amount',
            'Invoice Date',
            'Payment Due Date',
            'Status',
            'Description',
            'Created At',
            'Updated At'
        ])
        
        # Write invoice data
        for invoice in invoices:
            # Format dates in DD-MM-YYYY format
            invoice_date = ''
            if 'date' in invoice and invoice['date']:
                if isinstance(invoice['date'], datetime):
                    invoice_date = invoice['date'].strftime('%d-%m-%Y')
                else:
                    try:
                        # Try to parse if it's a string
                        date_obj = datetime.strptime(str(invoice['date']), '%Y-%m-%d')
                        invoice_date = date_obj.strftime('%d-%m-%Y')
                    except:
                        invoice_date = str(invoice['date'])
            
            due_date = ''
            if 'payment_due_date' in invoice and invoice['payment_due_date']:
                if isinstance(invoice['payment_due_date'], datetime):
                    due_date = invoice['payment_due_date'].strftime('%d-%m-%Y')
                else:
                    try:
                        # Try to parse if it's a string
                        date_obj = datetime.strptime(str(invoice['payment_due_date']), '%Y-%m-%d')
                        due_date = date_obj.strftime('%d-%m-%Y')
                    except:
                        due_date = str(invoice['payment_due_date'])
            
            created_at = ''
            if 'created_at' in invoice and invoice['created_at']:
                if isinstance(invoice['created_at'], datetime):
                    created_at = invoice['created_at'].strftime('%d-%m-%Y %H:%M:%S')
                else:
                    try:
                        # Try to parse if it's a string
                        date_obj = datetime.fromisoformat(str(invoice['created_at']).replace('Z', '+00:00'))
                        created_at = date_obj.strftime('%d-%m-%Y %H:%M:%S')
                    except:
                        created_at = str(invoice['created_at'])
            
            updated_at = ''
            if 'updated_at' in invoice and invoice['updated_at']:
                if isinstance(invoice['updated_at'], datetime):
                    updated_at = invoice['updated_at'].strftime('%d-%m-%Y %H:%M:%S')
                else:
                    try:
                        # Try to parse if it's a string
                        date_obj = datetime.fromisoformat(str(invoice['updated_at']).replace('Z', '+00:00'))
                        updated_at = date_obj.strftime('%d-%m-%Y %H:%M:%S')
                    except:
                        updated_at = str(invoice['updated_at'])
            
            writer.writerow([
                invoice.get('invoice_number', invoice.get('invoiceNumber', '')),
                invoice.get('client_name', invoice.get('clientName', '')),
                invoice.get('amount', 0),
                invoice_date,
                due_date,
                invoice.get('status', ''),
                invoice.get('description', ''),
                created_at,
                updated_at
            ])
        
        # Prepare response
        output.seek(0)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'invoices_export_{timestamp}.csv'
        
        # Create response with CSV data
        response = Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename={filename}'
            }
        )
        
        return response
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    # For local development
    app.run(debug=True, host='0.0.0.0', port=5000)
else:
    # For Vercel/production deployment
    # Vercel will use this as the WSGI application
    pass



