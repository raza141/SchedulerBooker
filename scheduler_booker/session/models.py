from django.db import models

from django.db import models
from django.contrib.auth.models import User
import stripe
from django.utils import timezone
from datetime import timedelta

class Student(models.Model):
    user_id = models.AutoField(primary_key=True)  # Auto incrementing primary key
    user_name = models.CharField(max_length=100)  # Full name of the student
    user_rate = models.DecimalField(max_digits=10, decimal_places=2)  # Session price (currency)
    email = models.EmailField(max_length=100, unique=True)  # Email field with unique constraint
    phone_number = models.CharField(max_length=15)  # Student's phone number
    join_date = models.DateField(default=timezone.now)  # Date the student joined
    status = models.CharField(max_length=10, choices=[('active', 'Active'), ('inactive', 'Inactive')], default='active')  # Active or inactive status
    
    # Additional fields
    total_sessions = models.IntegerField(default=0)  # Total number of sessions booked
    notes = models.TextField(blank=True)  # Additional notes about the student (optional)

    def __str__(self):
        return f'Name {self.user_name} and Contact: {self.phone_number}' 

class Tutor(models.Model):
    tutor_id = models.AutoField(primary_key=True)
    tutor_name = models.CharField(max_length=100)
    expertise = models.CharField(max_length=255)  # Subjects or topics they teach
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2)  # Rate per hour
    email = models.EmailField(max_length=100, unique=True)
    phone_number = models.CharField(max_length=15)
    availability = models.TextField()  # Days and times available for tutoring
    status = models.CharField(max_length=10, choices=[('active', 'Active'), ('inactive', 'Inactive')], default='active')

    def __str__(self):
        return f"Tutor Name {self.name}."

class Session(models.Model):
    session_id = models.AutoField(primary_key=True)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)  # Links session to a student
    session_date = models.DateField()  # Date of the session
    start_time = models.TimeField(null=True, blank=True)  # Start time (optional)
    end_time = models.TimeField(null=True, blank=True)  # End time (optional)
    place = models.CharField(max_length=100)  # Location of the session
    tutor_name = models.ForeignKey(Tutor, on_delete=models.CASCADE)
    topic_covered = models.CharField(max_length=255)  # Topic discussed during the session
    status = models.CharField(max_length=10, choices=[('pending', 'Pending'), ('confirmed', 'Confirmed')], default='pending')  # Session status

    def __str__(self):
        return f'Session with {self.student.user_name} on {self.session_date}'
    
    def save(self, *args, **kwargs):
        # When end_time is set, calculate payment
        if self.end_time:
            if not hasattr(self, 'payment'):
                # Create payment entry if it doesn't exist yet
                payment = Payment.objects.create(session=self)
            else:
                payment = self.payment

            # Calculate the price for the session based on student's rate
            payment.calculate_price()

        super(Session, self).save(*args, **kwargs)



class Payment(models.Model):
    PAYMENT_STATUS = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
    ]
    payment_id = models.AutoField(primary_key=True)
    session = models.OneToOneField('Session', on_delete=models.CASCADE)  # Link to the Session
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # Amount calculated based on duration
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')  # Status
    payment_date = models.DateTimeField(null=True, blank=True)  # Date of payment (set when paid)

    def __str__(self):
        return f'Payment for Session {self.session.id} - Status: {self.payment_status}'

    # Function to calculate the session price based on duration and tutor rate
    def calculate_price(self):
        duration = (self.session.end_time - self.session.start_time).total_seconds() / 3600  # Duration in hours
        self.amount = duration * self.session.Student.user_rate
        self.save()












class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=15)

class Tutor(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    availability = models.JSONField()  # Store available time slots as JSON

class Session(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    tutor = models.ForeignKey(Tutor, on_delete=models.CASCADE)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    confirmed = models.BooleanField(default=False)

    def check_overlap(self):
        overlapping_sessions = Session.objects.filter(
            tutor=self.tutor,
            start_time__lt=self.end_time,
            end_time__gt=self.start_time
        )
        return overlapping_sessions.exists()

class Payment(models.Model):
    session = models.ForeignKey(Session, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=10)  # e.g., "Pending", "Paid"
    stripe_payment_id = models.CharField(max_length=255, null=True, blank=True)

    def create_payment(self):
        # Stripe Payment Logic
        stripe.api_key = "your_stripe_secret_key"
        payment_intent = stripe.PaymentIntent.create(
            amount=int(self.amount * 100),  # Stripe uses cents
            currency='usd',
        )
        self.stripe_payment_id = payment_intent['id']
        self.save()
        return payment_intent
