# Invoice Dashboard - Indian Spices and Groceries

A modern, full-featured invoice management dashboard built with Python (Flask) and MongoDB. This application allows you to manage your company's invoices and track invoice status with monthly filtering and payment due date tracking.

## Features

- 🔐 **Admin Authentication**: Secure login system to protect your invoice data
- 📊 **Dashboard Overview**: View statistics including total invoices, total amount, paid and pending invoices
- 📅 **Monthly Invoice Filtering**: Filter and view invoices by month and year
- 📆 **Payment Due Date Tracking**: Track payment due dates with visual indicators for overdue invoices
- ➕ **Create Invoices**: Add new invoices with client information, amounts, dates, and status
- ✏️ **Edit Invoices**: Update existing invoice information (Full CRUD operations)
- 🗑️ **Delete Invoices**: Remove invoices from the system
- 🔍 **Search**: Search invoices by invoice number, client name, or description
- 📱 **Responsive Design**: Modern, mobile-friendly interface

## Tech Stack

- **Backend**: Python 3.x, Flask
- **Database**: MongoDB
- **Frontend**: HTML, CSS, JavaScript (Vanilla)

## Prerequisites

- Python 3.7 or higher
- MongoDB (local installation or MongoDB Atlas account)
- pip (Python package manager)

## Installation

1. **Clone or download this repository**

2. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up MongoDB**:
   - **Option 1: Local MongoDB**
     - Install MongoDB on your system
     - Start MongoDB service
     - Default connection: `mongodb://localhost:27017/`
   
   - **Option 2: MongoDB Atlas (Cloud)**
     - Create a free account at [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)
     - Create a cluster and get your connection string
     - Update the `MONGO_URI` in `.env` file

4. **Configure environment variables**:
   ```bash
   # Copy the example file
   cp config.example.txt .env
   
   # Edit .env and update with your MongoDB connection string
   # Also set your admin credentials:
   ADMIN_USERNAME=admin
   ADMIN_PASSWORD=your_secure_password
   SECRET_KEY=your-secret-key-here
   ```

## Running the Application

1. **Start the Flask server**:
   ```bash
   python app.py
   ```

2. **Open your browser** and navigate to:
   ```
   http://localhost:5000
   ```

## Usage

### Login

1. Navigate to the application URL
2. Enter your admin username and password
3. Default credentials (change in production):
   - Username: `admin`
   - Password: `admin123`

### Adding a New Invoice

1. Click the "Add New Invoice" button
2. Fill in the required fields:
   - Invoice Number
   - Client Name
   - Amount
   - Status (Pending/Paid/Overdue)
   - Invoice Date
   - Payment Due Date
   - Description (optional)
3. Click "Save Invoice"

### Editing an Invoice

1. Click the "Edit" button on any invoice row
2. Modify the fields as needed
3. Click "Save Invoice"

### Deleting an Invoice

1. Click the "Delete" button on any invoice row
2. Confirm the deletion

### Filtering Invoices by Month

- Use the month and year dropdown filters to view invoices for a specific month
- Select "All Months" and "All Years" to view all invoices

### Searching Invoices

- Use the search box to filter invoices by invoice number, client name, or description

### Downloading Invoice Files

- (Not applicable) - File attachments are not supported in this version

### Payment Due Date

- Payment due dates are displayed in the invoice table
- Overdue invoices (past due date and not paid) are highlighted in red

## API Endpoints

- `GET /api/invoices` - Get all invoices
- `POST /api/invoices` - Create a new invoice
- `GET /api/invoices/<id>` - Get a specific invoice
- `PUT /api/invoices/<id>` - Update an invoice
- `DELETE /api/invoices/<id>` - Delete an invoice

## Project Structure

```
.
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── .env.example          # Environment variables template
├── .gitignore            # Git ignore file
├── README.md             # This file
├── templates/
│   └── index.html        # Dashboard HTML
└── static/               # Static assets (if any)
```

## Configuration

You can customize the application by modifying:

- **Port**: Change the port in the `app.run()` call at the bottom of `app.py`

## Troubleshooting

### MongoDB Connection Issues

- Ensure MongoDB is running (if using local installation)
- Check your connection string in `.env` file
- Verify network connectivity (if using MongoDB Atlas)
- Check firewall settings

### File Attachments

- File attachments are not supported in this version. Consider integrating a cloud storage service if you need this feature.

## Security Notes

- **Change default credentials**: Update `ADMIN_USERNAME` and `ADMIN_PASSWORD` in your `.env` file
- **Change secret key**: Update `SECRET_KEY` in your `.env` file for production
- For production use, also consider:
  - Using HTTPS
  - Adding rate limiting
  - Regular security updates
  - Integrating secure file storage if you later add attachments

## License

This project is open source and available for use.

## Support

For issues or questions, please check the code comments or create an issue in the repository.

