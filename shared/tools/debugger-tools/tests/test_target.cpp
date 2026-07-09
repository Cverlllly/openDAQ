#include <opendaq/opendaq.h>

#include <cstdio>

using namespace daq;

void breakpoint_here()
{
    std::puts("test target: at breakpoint");
}

int main()
{
    StringPtr str = String("hello");
    StringPtr emptyStr = String("");
    ObjectPtr<IInteger> intVal = Integer(42);
    ObjectPtr<IInteger> negIntVal = Integer(-7);
    ObjectPtr<IFloat> floatVal = Floating(3.5);
    ObjectPtr<IBoolean> boolTrue = Boolean(true);
    ObjectPtr<IBoolean> boolFalse = Boolean(false);
    RatioPtr ratio = Ratio(1, 2);
    ComplexNumberPtr complexVal = ComplexNumber(3.0, 4.0);
    ComplexNumberPtr complexNeg = ComplexNumber(1.5, -2.5);
    BinaryDataPtr binData = BinaryData(static_cast<SizeT>(16));

    StringPtr nullStr;

    IString* rawStr = str.getObject();

    ListPtr<IString> strList = List<IString>("one", "two", "three");
    ListPtr<IInteger> intList = List<IInteger>(10, 20);
    ListPtr<IBaseObject> emptyList = List<IBaseObject>();

    DictPtr<IString, IInteger> dict = Dict<IString, IInteger>();
    dict.set("a", 1);
    dict.set("b", 2);
    DictPtr<IString, IInteger> emptyDict = Dict<IString, IInteger>();

    TypeManagerPtr typeManager = TypeManager();
    auto enumType = EnumerationType("Colors", List<IString>("Red", "Green", "Blue"));
    typeManager.addType(enumType);
    EnumerationPtr enumVal = Enumeration("Colors", "Green", typeManager);

    auto structFields = Dict<IString, IBaseObject>();
    structFields.set("FieldA", String("abc"));
    structFields.set("FieldB", Integer(7));
    StructPtr structVal = Struct("MyStruct", structFields, typeManager);

    PropertyObjectPtr propObj = PropertyObject();
    propObj.addProperty(IntProperty("Frequency", 50));
    propObj.addProperty(StringProperty("Label", "test"));
    propObj.addProperty(FloatProperty("Scale", 1.5));

    breakpoint_here();
    return 0;
}
