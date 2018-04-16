
from autoIntern.models import Document
from autoIntern.models import User
from autoIntern.forms import UserForm
from django.test import TestCase
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.files import File
import os
from django.conf import settings
from autoIntern.helpers import GetDocumentByHeader, get_documents, get_cases, get_docs_in_case, valid_file_type



class NoteUploadTest(TestCase):
    def setUp(self):
        form = UserForm({
            'username': 'Test',
            'email' : 'test@test.com',
            'first_name': 'test',
            'last_name': 'test',
            'password': 'test'
        })
        if form.is_valid():
            form.save()
        user = User.objects.get(username="Test")
        content = b'This is a test note'
        note_name = 'new_note_name'
        note = default_storage.save('static/document_folder/testing_note.txt',
                             ContentFile(content))


    def test_note(self):
        setUp()
        doc = Document(GetDocumentByHeader(file, user, False, note_name))
        content = doc.file.read()
        self.assertEquals(content, b'This is a test note')



    def test_document_save(self):
        setUp()
        doc = Document.objects.get(doc_id='testing_note.txt')
        content = str(doc.file.url).replace("%2F", "/")
        self.assertEquals(content, 'https://storage.googleapis.com/autointern-dev/static/document_folder/testing_note.txt')