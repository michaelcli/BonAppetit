from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect
from django.template import RequestContext, loader
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView
from PIL import Image
import pandas as pd
from fbprophet import Prophet
import string
import math
import datetime
import numpy as np
import csv
from ooglorp.forms import StatsForm, EntryForm
from ooglorp.models import Food

#function to retrain the model based on the new data
#returns model object
def update_csv(csv_path, value):
    with open(csv_path, 'ab') as csvfile:
        spamwriter = csv.writer(csvfile)
        date = datetime.date.today()
        date = date.strftime('%Y-%d-%m')
        temp = date
        spamwriter.writerow([])
        spamwriter.writerow([temp, value])

def retrain(csv_path):
    df = pd.read_csv(csv_path)
    df.head()
    m = Prophet()
    m.fit(df)
    return m

def find_adjusted_food_order(demand_csv, sell_csv, month_after):
    #create models for both inventory and wastage
    date = datetime.date.today() + pd.DateOffset(months=month_after)
    inventory_model = retrain(demand_csv)
    waste_model = retrain(sell_csv)
    inventory = predict_date(date, inventory_model, month_after)
    waste = predict_date(date, waste_model, month_after)
    #return adjusted amount for needed date
    return inventory - waste

def predict_date(date, model, period):
    #make dataframe
    #current date - last date in training + period
    period = int(((pd.to_datetime("today") - list(model.history['ds'])[-1])/np.timedelta64(1, 'M'))) + period
    #period = pd.to_datetime("today") - list(model.history['ds'])[-1] + pd.offsets.MonthOffset(period)
    future = model.make_future_dataframe(periods=50*period)
    #add to tail
    future.tail()
    #make prediction
    forecast = model.predict(future)
    forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail()
    #change to standard times
    forecast['ds'] = pd.to_datetime(forecast['ds'])
    date_formatted = pd.Timestamp(date)
    list_index = list(forecast['ds']).index(date_formatted)
    return list(forecast['yhat_lower'])[list_index]

# Create your views here.
@csrf_exempt
def index(request):
    food_pickup_info=''
    if(request.method == 'POST'):
        #if the button clicked on was food x, delete it and record info for user
        for food in list(Food.objects.all()):
            if(food.key in request.POST):
                chosen_food = food
                print(chosen_food.name)
                food_pickup_info = "Get your " + chosen_food.name + "s at " + chosen_food.address + \
                " before " + chosen_food.expiration
                chosen_food.delete()
    template_name = 'index.html'
    all_entries = Food.objects.all() #get all foods
    return render(request, 'index.html', {'food_list':list(all_entries), 'food_pickup_info':food_pickup_info})

#the csrf cookie crashes any posting of content to server so disable
@csrf_exempt
def upload(request):
    template_name = 'upload.html'
    #if an image is uploaded
    if(request.method == 'POST' and request.POST['name'] is not None):
        food = Food(name=request.POST['name'], amount = request.POST['amount'], \
        expiration=request.POST['expiration'], address=request.POST['address'])
        food.key = food.address + food.name + food.amount
        food.save() #save in database
        return render(request, 'upload.html',{'result':'Uploaded food!'})
    else:
        return render(request, 'upload.html', {'result':''})

#the csrf cookie crashes any posting of content to server so disable
@csrf_exempt
def stats(request):
    template_name = 'stats.html'
    #if an image is uploaded
    if(request.method == 'POST' and request.POST['estimate'] is not None):
        estimate = int(request.POST['estimate'])
        result = find_adjusted_food_order('ooglorp-master/monthly_tomatoes.csv', 'ooglorp-master/sell.csv', estimate)
        result = str(round(result)) + ' apples'
        return render(request, 'stats.html',{'result':result, 'estimation':"Estimated optimal order in " + str(estimate)+ " months: "})
    else:
        return render(request, 'stats.html', {'result':'', 'estimation':'Estimate your optimal order in ___ months: '})
