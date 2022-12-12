import xml.etree.ElementTree as elemTree
import os
import sys

class ConfigManager:
  def __init__(self, config_path='.config.template.xml'):
    self.config_path = config_path
    self.tree = elemTree.parse(self.config_path)
    self.root = self.tree.getroot()
    # print(self.root.find('./PATHS').find('work').text)

  def get_work_path(self):
    return self.root.find('./PATHS').find('work').text

  def get_path(self, tag):
    return self.root.find('./PATHS').find(tag).text
  
  def get_database(self, dbtype='sqlite3'):
    node = self.root.find('./DBMS').find(dbtype)
    print(node)
    return {tag:node.find(tag).text for tag in ['database']}

  def get_tables(self):
    """
    테이블 정보: dict
    """
    tables = self.root.find('./DBMS/tables')
    dic = {}
    for table in tables.findall('table'):
      dic[table.attrib['type']] ={  
      'table_name':table.find('name').text, 
      'drop_table':True if table.find('drop_table').text=='1' else False
      }
    return dic

  def get_model_info(self, tag):
    model = self.root.find('./Models').find(tag)
    return {
      'model_path': model.find('model_path').text,
      'description': model.find('description').text
    }
  
  def retrieve_candidate_ETFs(self):
    """
    실전에 참여할 후보 ETF 종목 코드: list
    """
    candidates = self.root.find('./Candidates')
    return [(code.text, code.attrib['desc'], code.attrib['action_tag']) for code in candidates.findall('code')]

# print(ConfigManager.__init__);