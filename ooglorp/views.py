import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
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
import pandas as pd
from ooglorp.forms import StatsForm, EntryForm
from ooglorp.models import Food
import seaborn as sns
sns.set() #matplotlib style

#function to retrain the model based on the new data
#returns model object
def update_csv(csv_path, value):
    with open(csv_path, 'a') as csvfile:
        spamwriter = csv.writer(csvfile)
        date = datetime.date.today() - datetime.timedelta(weeks=4)
        date = date.strftime('%m/%d/%Y')
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
    future = model.make_future_dataframe(periods=90*period)
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
                food_pickup_info = "Get your " + chosen_food.name + " at " + chosen_food.address + \
                " before " + chosen_food.expiration + ", contact " + chosen_food.phone
                chosen_food.delete()
    template_name = 'index.html'
    all_entries = Food.objects.all() #get all foods
    return render(request, 'index.html', {'food_list':list(all_entries), 'food_pickup_info':food_pickup_info})

def save_wasted():
    df = pd.read_csv('./ooglorp-master/monthly_tomatoes_ooglorp.csv')
    x = list(df['ds'])
    dates = []
    y = list(df['y'])
    for date in x:
        s = date.rstrip()
        dates.append(datetime.datetime.strptime(s, "%m/%d/%Y").date())
        #date = s.strftime("%Y%m%d")
        #date = datetime(year=int(s[0:4]), month=int(s[0:2]), day=int(s[6:8]))
    x = matplotlib.dates.date2num(dates)
    #print(x, y)
    plt.plot_date(x,y, 'k', color='mediumvioletred')
    plt.xlabel('Dates')
    plt.ylabel('Apples wasted')
    plt.title('Apples wasted across time')
    plt.savefig('ooglorp/static/images/wasted.jpg')

def save_ordered():
    df = pd.read_csv('./ooglorp-master/monthly_tomatoes.csv')
    x = list(df['ds'])
    dates = []
    y = list(df['y'])
    for date in x:
        s = date.rstrip()
        dates.append(datetime.datetime.strptime(s, "%m/%d/%Y").date())
        #date = s.strftime("%Y%m%d")
        #date = datetime(year=int(s[0:4]), month=int(s[0:2]), day=int(s[6:8]))
    x = matplotlib.dates.date2num(dates)
    plt.plot_date(x, y, 'k', color='mediumvioletred')
    plt.xlabel('Dates')
    plt.ylabel('Apples ordered')
    plt.title('Apples ordered across time')
    plt.savefig('ooglorp/static/images/ordered.jpg')

#the csrf cookie crashes any posting of content to server so disable
@csrf_exempt
def upload(request):
    template_name = 'upload.html'
    #if an image is uploaded
    if(request.method == 'POST' and request.POST['name'] is not None):
        food = Food(name=request.POST['name'], amount = request.POST['amount'], \
        expiration=request.POST['expiration'], address=request.POST['address'],phone=request.POST['phone'])
        food.key = food.address + food.name + food.amount
        food.save() #save in database
        return render(request, 'upload.html',{'result':'Uploaded food!'})
    else:
        return render(request, 'upload.html', {'result':''})

@csrf_exempt
def feed(request):
    return render(request, 'feed.html', {'feed_image':'output.jpg'})

#the csrf cookie crashes any posting of content to server so disable
@csrf_exempt
def stats(request):
    template_name = 'stats.html'
    plt.clf()
    save_wasted()
    plt.clf()
    save_ordered()
    plt.clf()
    #if an image is uploaded
    if(request.method == 'POST' and request.POST['order'] is not None):
        order= int(request.POST['order'])
        update_csv('ooglorp-master/monthly_tomatoes_ooglorp.csv', order)
        result = find_adjusted_food_order('ooglorp-master/monthly_tomatoes.csv', 'ooglorp-master/monthly_tomatoes_ooglorp.csv', 1) #predict one month ahead
        result = str(round(result)) + ' apples'
        return render(request, 'stats.html',{'result':result, 'estimation':"Estimated optimal order of apples in next month: "})
    else:
        return render(request, 'stats.html', {'result':'', 'estimation':'Input your order of apples this month and get the estimate for next month\'s optimal order: '})
