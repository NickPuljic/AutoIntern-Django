from django.http import HttpResponse, HttpResponseRedirect
from django.template import loader
from django.shortcuts import render, render_to_response
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from autoIntern.forms import UserForm
from autoIntern import models
from autoIntern.parse_identifiers import GetDocumentByHeader
import json
import csv
from django.core.exceptions import ObjectDoesNotExist


def index(request):
    # Check if user is logged in
    if request.user.is_authenticated:
        context = {'documents': get_documents(), 'cases' : get_cases(request)}
    else:
        context = {'userForm': UserForm()}

    return render(request, 'autoIntern/homePage.html', context)


def userLogin(request):
    """Login Users"""
    if request.method == 'POST':
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)

        context = {'userForm': UserForm()}

        # User successfully authenticated
        if user is not None:
            login(request, user)
            context = {'documents': get_documents(), 'cases' : get_cases(request)}
        return render(request, 'autoIntern/homePage.html', context)


def userLogout(request):
    """Defines the logout behavior"""
    if request.method == 'POST':
        logout(request)
        return HttpResponseRedirect('/')


def register(request):
    """Register Users"""
    userForm = UserForm()
    if request.method == 'POST':
        userForm = UserForm(request.POST)
        if userForm.is_valid():
            user = userForm.save()
        return HttpResponseRedirect('/')
    if request.method == 'GET':
        return HttpResponseRedirect('/')


# TODO: Move
def get_documents():
    return models.Document.objects.all()

# TODO: Move
def get_cases(request):
    return models.Case.objects.all().filter(user_permissions=request.user)

# TODO: Move
def get_docs_in_case(case_id):
    case = models.Case.objects.get(case_id = case_id)
    documents = []

    for document in case.documents.all():
        documents.append(document)

    return documents

@login_required(redirect_field_name='', login_url='/')
def viewDocument(request):
    if request.method == 'GET':
        try:
            cur_doc_id = request.GET['id']
            document = models.Document.objects.get(doc_id=cur_doc_id)
            file = document.file.read().decode('utf-8')
            context = {'file': file}
            return render(request, 'autoIntern/viewDocument.html', context)
        except:
            context = {'documents': get_documents()}
            return render(request, 'autoIntern/viewDocument.html', context)


@login_required(redirect_field_name='', login_url='/')
def viewCase(request):
    try:
        if request.method == 'GET':
            cur_case_id = request.GET['id']
        if request.method == 'POST':
            cur_case_id = request.POST['case_id']

        case = models.Case.objects.get(case_id=cur_case_id)
        user = User.objects.get(username=request.user)

        user_perms = models.Permissions.objects.all().filter(case=case, user=user)

        #If user types in case ID, redirect
        if user_perms.count() == 0:
            return HttpResponseRedirect('/')

        case_name = case.case_name
        documents = get_docs_in_case(cur_case_id)
        context = {'documents': documents, 'case_name': case_name, 'case_id': cur_case_id}

        # If manager, add to context
        if user_perms.filter(user_type=models.Permissions.MANAGER_USER).count() > 0:
            context['is_manager'] = True
            users = User.objects.all()
            case_users = models.Permissions.objects.filter(case=case)
            case_usernames = []

            for u in case_users:
                case_usernames.append(u.user.username)

            # List of users not currently in case
            list = [user for user in users if user.username not in case_usernames and user.username != 'admin']
            context['users'] = list

        else:
            context['is_manager'] = False

        return render(request, 'autoIntern/viewCase.html', context)

    except Exception as e:
        print(e)
        return HttpResponseRedirect('/')


# TODO: Check and simplify conditional flow (if / else)
@login_required(redirect_field_name='', login_url='/')
def upload(request):
    '''Handles Local file uploads'''
    if request.method == 'POST':
        if not request.user.is_authenticated:
            return HttpResponseRedirect('/')

        user = User.objects.get(username=request.user)

        new_document = None
        try:
            if request.FILES['uploadFile'] is not None:
                new_document = GetDocumentByHeader(request.FILES['uploadFile'], user)

        # just reroutes to homepage if try to upload nothing
        # @TODO handle the null exception better
        except KeyError:
            if request.POST['uploadFile'] == '':
                return HttpResponseRedirect('/')

        if new_document[0] == False and 'case_id' in request.POST:
            case = models.Case.objects.get(case_id=request.POST['case_id'])
            cur_case_id = case.case_id
            case_name = case.case_name
            existing_doc = models.Document.objects.get(doc_id = new_document[1])
            case.documents.add(existing_doc)
            documents = get_docs_in_case(cur_case_id)
            context = {'documents': documents, 'case_name': case_name, 'case_id': cur_case_id, 'upload_fail':True}
            return render(request, 'autoIntern/viewCase.html', context)

        if new_document[0] == False:
            context = {'documents': get_documents(), 'cases': get_cases(request), 'upload_fail': True}
            return render(request, 'autoIntern/homePage.html', context)


        if 'case_id' in request.POST:
            case = models.Case.objects.get(case_id=request.POST['case_id'])
            cur_case_id = case.case_id
            case.documents.add(new_document)
            case_name = case.case_name
            documents = get_docs_in_case(cur_case_id)
            context = {'documents': documents, 'case_name': case_name, 'case_id': cur_case_id}

            return render(request, 'autoIntern/viewCase.html', context)

        else:
            context = {'documents': get_documents(), 'cases' : get_cases(request)}
            return render(request, 'autoIntern/homePage.html', context)
    else:
        return HttpResponseRedirect('/')

@login_required(redirect_field_name='', login_url='/')
def exportTags(request):
    ''' Exports tags associated with document'''
    # Tags to be exported:
    TAGS = ['company', 'doc_type', 'doc_date']

    if request.method == 'POST':
        try:
            path = request.POST['path']
            doc_id = path.split("=", maxsplit=1)[1]
            doc = models.Document.objects.get(doc_id=doc_id)
            vals = doc.__dict__

            #dict_tags => contains tags and corresponding values
            dict_tags = {tag : vals[tag] for tag in TAGS}

            #Create json
            js = json.dumps(dict_tags)
            conv = json.loads(js)

            if 'csv' in request.POST:
                # Create the HttpResponse object with the appropriate CSV header.
                response = HttpResponse(content_type='text/csv; charset=utf8')
                response['Content-Disposition'] = 'attachment; filename="%s_%s_%s_tags.csv"' % (vals[TAGS[0]], vals[TAGS[1]], vals[TAGS[2]])

                writer = csv.writer(response)
                for tag in TAGS:
                    writer.writerow([tag, conv[tag]])

            elif 'txt' in request.POST:
                out = ''
                for k, v in conv.items():
                    out += k
                    out += ': '
                    out += v
                    out += '\r\n'

                # Remove the last, unnecessary newline
                out = out[:-2]

                # Create the HttpResponse object with the appropriate TXT header.
                response = HttpResponse(out, content_type='text/plain; charset=utf8')
                response['Content-Disposition'] = 'attachment; filename="%s_%s_%s_tags.txt"' % (vals[TAGS[0]], vals[TAGS[1]], vals[TAGS[2]])

            elif 'json' in request.POST:
                response = HttpResponse(js, content_type='application/javascript; charset=utf8')
                response['Content-Disposition'] = 'attachment; filename="%s_%s_%s_tags.json"' % (vals[TAGS[0]], vals[TAGS[1]], vals[TAGS[2]])

            else:
                return HttpResponseRedirect('/')

            return response
        except:
            return HttpResponseRedirect('/')
    else:
        return HttpResponseRedirect('/')


# TODO: Alert user to a repeated case name (handles repeat)
@login_required(redirect_field_name='', login_url='/')
def createCase(request):
    currUser = User.objects.get(username=request.user)
    new_case = None
    name = request.POST['caseName']
    case_exists = None
    try:
        case = models.Case.objects.get(case_name=name)
        case_exists = True
    except ObjectDoesNotExist:
        case_exists = False

    if case_exists == True:
        new_case = models.Case(case_name=name+'(1)')
    else:
        new_case = models.Case(case_name = name)

    new_case.save()
    new_case.user_permissions.add(currUser)

    new_perm = models.Permissions(user=currUser, case=new_case, user_type=models.Permissions.MANAGER_USER)
    new_perm.save()

    if request.user.is_authenticated:
        context = {'documents': get_documents(), 'cases': get_cases(request)}
    else:
        context = {'userForm': UserForm()}

    return render(request, 'autoIntern/homePage.html', context)

def addUsers(request):
    ids = request.POST.getlist('ids[]')
    case_id = request.POST['case_id']

    case = models.Case.objects.get(case_id=case_id)

    for id in ids:
        user = User.objects.get(username=id)
        case.user_permissions.add(user)

        new_perm = models.Permissions(user=user, case=case, user_type=models.Permissions.BASE_USER)
        new_perm.save()

    case_name = case.case_name
    documents = get_docs_in_case(case_id)
    context = {'documents': documents, 'case_name': case_name, 'case_id': case_id}

    return (viewCase(request))