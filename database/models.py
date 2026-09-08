class Leave(Base):
    __tablename__ = 'leaves'
    id = Column(Integer, primary_key=True)
    region_id = Column(Integer, ForeignKey('regions.id'), nullable=False)
    employee_name = Column(String, nullable=False)
    leave_date = Column(Date, nullable=False)
    notes = Column(String, nullable=True)
